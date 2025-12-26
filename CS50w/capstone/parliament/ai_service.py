import google.generativeai as genai
from django.conf import settings
from pydantic import BaseModel, Field
from typing import Optional
import json

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

class InterestExtraction(BaseModel):
    """Structured data model for interest extraction"""
    sector: str = Field(description="Industry sector (e.g., Energy, Finance, Healthcare)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    payer: Optional[str] = Field(description="Company or organization name")
    value: Optional[float] = Field(description="Estimated monetary value in GBP")
    is_current: bool = Field(default=True, description="Whether interest is currently active")


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
1. SECTOR: Choose from: Energy, Finance, Healthcare, Real Estate, Technology, Media, Legal, Consulting, Agriculture, Transport, Public Service, Social Welfare, Education, Diplomacy, Other
2. PAYER: The company or organization name
3. VALUE: Estimated monetary value in GBP (if mentioned or can be reasonably estimated)
4. IS_CURRENT: true if currently active, false if past/historical
5. CONFIDENCE: Your confidence in the extraction (0.0 to 1.0 MAKE SURE TO PROVIDE IT IN DECIMAL FORMAT)

Interest declaration:
"{summary_text}"

Respond ONLY with valid JSON in this exact format (no markdown, no explanation):
{{
  "sector": "Energy",
  "confidence": 0.95,
  "payer": "Company Name Ltd",
  "value": 50000,
  "is_current": true
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
            'sector': validated.sector,
            'confidence': validated.confidence,
            'payer': validated.payer,
            'value': validated.value,
            'is_current': validated.is_current
        }
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response was: {text}")
        return {
            'sector': 'Other',
            'confidence': 0.0,
            'payer': None,
            'value': None,
            'is_current': True
        }
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            'sector': 'Other',
            'confidence': 0.0,
            'payer': None,
            'value': None,
            'is_current': True
        }