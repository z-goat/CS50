import google.generativeai as genai
from django.conf import settings
from pydantic import BaseModel, Field
from typing import Optional
import json

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class InterestExtraction(BaseModel):
    interest_type: str = Field(description="AI-determined interest type")
    sector: str = Field(description="Industry sector (e.g., Energy, Finance, Healthcare)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    payer: Optional[str] = Field(description="Company or organization name")
    value: Optional[float] = Field(description="Estimated monetary value in GBP")
    is_current: bool = Field(default=True, description="Whether interest is currently active")
    summary: Optional[str] = Field(description="Brief summary")
    
class DivisionTagExtraction(BaseModel):
    sectors: list[str] = Field(default_factory=list, description="List of sector strings")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


def extract_interest_data(summary_text: str) -> dict:
    """
    Use Gemini to extract structured data from interest summary
    
    Args:
        summary_text: Raw text from MP's interest declaration
        
    Returns:
        dict with keys: sector, confidence, payer, value, is_current
    """
    
    model = genai.GenerativeModel('gemma-3-27b-it')
    
    prompt = f"""You are a data extraction system analyzing UK Parliamentary financial interest declarations.

Extract the following information from this interest declaration:
1. INTEREST_TYPE: Choose one of the following types:
   - shareholding
   - consultancy
   - speech
   - gift
   - trusteeship
   - donation
   - property
   - other
2. SECTOR: Choose from: Energy, Finance, Healthcare, Real Estate, Technology, Media, Legal, Consulting, Agriculture, Transport, Public Service, Social Welfare, Education, Diplomacy, Other
3. PAYER: The company or organization name
4. VALUE: Estimated monetary value in GBP (if mentioned or can be reasonably estimated)
5. IS_CURRENT: true if currently active, false if past/historical
6. CONFIDENCE: Your confidence in the extraction (0.0 to 1.0 MAKE SURE TO PROVIDE IT IN DECIMAL FORMAT)
7. SUMMARY: A brief summary of the interest no longer than 30 words

Interest declaration:
"{summary_text}"

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "interest_type": "consultancy",  
  "sector": "Energy",
  "confidence": 0.95,
  "payer": "Company Name Ltd",
  "value": 50000,
  "is_current": true,
  "summary": "Payment received for consultancy on renewable energy projects."
}}

If information is not available, use null for that field. Be conservative with estimates."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown fences if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0]
        text = text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON
        data = json.loads(text)
        
        # If the confidence is given as a percentage, convert to decimal
        if isinstance(data.get("confidence"), (int, float)) and data["confidence"] > 1:
            data["confidence"] = data["confidence"] / 100
            
        # Clean and convert value to float if possible    
        raw_value = data.get("value")
        
        if isinstance(raw_value, str):
            cleaned = raw_value.replace("£", "").replace(",", "").strip()
            try:
                data["value"] = float(cleaned)
            except ValueError:
                data["value"] = None

        # Validate with Pydantic
        validated = InterestExtraction(**data)
        
        return {
            'interest_type': validated.interest_type,
            'sector': validated.sector,
            'confidence': validated.confidence,
            'payer': validated.payer,
            'value': validated.value,
            'is_current': validated.is_current,
            'summary': validated.summary,
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {text}")
        return {
            'interest_type': "other",
            'sector': 'Other',
            'confidence': 0.0,
            'payer': None,
            'value': None,
            'is_current': True,
            'summary': None
        }
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            'interest_type': "other",
            'sector': 'Other',
            'confidence': 0.0,
            'payer': None,
            'value': None,
            'is_current': True,
            'summary': None
        }
        


def extract_division_tags(title: str, description: str = "") -> dict:
    """
    Use Gemini to categorize a division into policy sectors.
    
    Args:
        title: Division title
        description: Optional division description
        
    Returns:
        dict with keys: sectors (list of strings), confidence (float)
    """
    model = genai.GenerativeModel('gemma-3-27b-it')
    prompt = f"""
You are an AI that categorizes UK parliamentary votes into policy areas.
Classify the following vote into sectors (choose from Energy, Finance, Healthcare, Real Estate, Technology, Media, Legal, Consulting, Agriculture, Transport, Public Service, Social Welfare, Education, Diplomacy, Other).

Title: "{title}"
Description: "{description}"

Respond ONLY with valid JSON:
{{
  "sectors": ["Finance", "Energy"],
  "confidence": 0.95
}}
If unsure, pick the most relevant sector.
"""
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown if present
        text = text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(text)
        
        validated = DivisionTagExtraction(**data)
        return {
            "sectors": validated.sectors,
            "confidence": validated.confidence
        }
    except Exception as e:
        print(f"Division tagging error: {e}")
        return {
            "sectors": ["Other"],
            "confidence": 0.0
        }


class ConflictAnalysis(BaseModel):
    has_conflict: bool = Field(description="Whether a conflict of interest exists")
    conflict_score: float = Field(ge=0.0, le=1.0, description="Conflict severity 0-1")
    reasoning: str = Field(description="Explanation of the conflict analysis")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this assessment")


def analyze_conflict_with_ai(member_name: str, interests: list[dict], division_title: str, division_description: str = "") -> dict:
    """
    Use AI to analyze whether a member's financial interests conflict with their vote on a division.
    
    Args:
        member_name: Name of the MP
        interests: List of interest dicts with keys: summary, sector, payer, value
        division_title: Title of the parliamentary division/vote
        division_description: Optional description of what the division is about
        
    Returns:
        dict with keys: has_conflict, conflict_score (0-1), reasoning, confidence
    """
    
    model = genai.GenerativeModel('gemma-3-27b-it')
    
    # Format interests for the prompt
    interests_text = "\n".join([
        f"- {i.get('summary', 'No description')} "
        f"({i.get('sector', 'Unknown sector')} sector, "
        f"from {i.get('payer', 'Unknown payer')}, "
        f"value: £{i.get('value', 'Not disclosed')})"
        for i in interests
    ])
    
    prompt = f"""You are an expert in UK parliamentary ethics and conflict of interest analysis.

Analyze whether this MP's financial interests conflict with their vote on a particular division.

MP NAME: {member_name}

DECLARED FINANCIAL INTERESTS:
{interests_text}

PARLIAMENTARY DIVISION (Vote):
Title: "{division_title}"
Description: "{division_description}"

TASK:
1. Determine if any of these financial interests could reasonably be affected by this vote
2. Assess the SEVERITY of the conflict (if any exists) on a scale where:
   - 0.0-0.2: No meaningful conflict or very minor interest
   - 0.2-0.4: Weak conflict - interest may be tangentially affected
   - 0.4-0.6: Moderate conflict - interest could be meaningfully affected
   - 0.6-0.8: Strong conflict - interest is directly affected
   - 0.8-1.0: Severe conflict - interest heavily depends on vote outcome

3. Provide clear reasoning for your assessment
4. Rate your confidence in this analysis (0.0 to 1.0)

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "has_conflict": true,
  "conflict_score": 0.75,
  "reasoning": "The MP has significant holdings in energy companies that would be affected by renewable energy regulations discussed in this vote.",
  "confidence": 0.85
}}
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean markdown if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0]
        text = text.replace('```json', '').replace('```', '').strip()
        
        data = json.loads(text)
        validated = ConflictAnalysis(**data)
        
        return {
            'has_conflict': validated.has_conflict,
            'conflict_score': validated.conflict_score,
            'reasoning': validated.reasoning,
            'confidence': validated.confidence,
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error in conflict analysis: {e}")
        return {
            'has_conflict': False,
            'conflict_score': 0.0,
            'reasoning': "Error analyzing conflict",
            'confidence': 0.0,
        }
    except Exception as e:
        print(f"Conflict analysis error: {e}")
        return {
            'has_conflict': False,
            'conflict_score': 0.0,
            'reasoning': f"Error: {str(e)}",
            'confidence': 0.0,
        }
