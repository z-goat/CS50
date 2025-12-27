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