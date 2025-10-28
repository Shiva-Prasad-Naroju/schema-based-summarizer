"""
Utility functions for FIR Auto-Fill System
Helper functions for data processing, validation, and formatting
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import json


class FIRValidator:
    """Validator class for FIR data fields"""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate Indian phone number format"""
        # Remove spaces and special characters
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        # Check for 10 digit Indian mobile number
        pattern = r'^[6-9]\d{9}$'
        return bool(re.match(pattern, phone_clean))
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date in YYYY-MM-DD format"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_time(time_str: str) -> bool:
        """Validate time in HH:MM format"""
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def clean_phone(phone: str) -> str:
        """Clean and format phone number"""
        # Remove all non-digit characters
        phone_digits = re.sub(r'\D', '', phone)
        # Take last 10 digits if more than 10
        if len(phone_digits) > 10:
            phone_digits = phone_digits[-10:]
        return phone_digits


class TextProcessor:
    """Process and extract information from complaint text"""
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """Extract potential dates from text"""
        # Common date patterns
        patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',  # DD-MM-YYYY or MM-DD-YYYY
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',      # YYYY-MM-DD
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',  # DD Month YYYY
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}'  # Month DD, YYYY
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates
    
    @staticmethod
    def extract_times(text: str) -> List[str]:
        """Extract potential times from text"""
        # Time patterns
        patterns = [
            r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?',  # HH:MM AM/PM
            r'\d{1,2}\s*(?:AM|PM|am|pm)',          # H AM/PM
            r'around\s+\d{1,2}(?::\d{2})?'         # around HH:MM
        ]
        
        times = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            times.extend(matches)
        
        return times
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract potential phone numbers from text"""
        # Indian phone number patterns
        patterns = [
            r'[6-9]\d{9}',                        # 10 digit starting with 6-9
            r'\+91[-\s]?[6-9]\d{9}',             # With country code
            r'0\d{2,4}[-\s]?\d{6,8}'             # Landline
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        return phones
    
    @staticmethod
    def extract_amounts(text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts from text"""
        # Amount patterns
        patterns = [
            (r'(?:Rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:lakh|lakhs|L)?', 'INR'),
            (r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rupees|Rs\.?|INR)', 'INR'),
        ]
        
        amounts = []
        for pattern, currency in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean amount string
                amount_str = re.sub(r'[,\s]', '', match)
                try:
                    amount = float(amount_str)
                    # Handle lakh conversion
                    if 'lakh' in text[text.find(match):text.find(match)+20].lower():
                        amount *= 100000
                    amounts.append({'amount': amount, 'currency': currency})
                except ValueError:
                    continue
        
        return amounts
    
    @staticmethod
    def identify_offense_keywords(text: str) -> List[str]:
        """Identify potential offense types from keywords in text"""
        offense_keywords = {
            'theft': ['steal', 'stole', 'stolen', 'theft', 'thief', 'snatched', 'snatch', 'took away'],
            'robbery': ['rob', 'robbed', 'robbery', 'loot', 'looted', 'held up', 'gun point', 'knife point'],
            'assault': ['beat', 'beaten', 'hit', 'attack', 'attacked', 'assault', 'hurt', 'injured', 'wound'],
            'fraud': ['fraud', 'cheat', 'cheated', 'deceive', 'scam', 'fake', 'forged', 'forgery'],
            'extortion': ['extort', 'extortion', 'demand', 'ransom', 'threaten for money'],
            'harassment': ['harass', 'harassment', 'trouble', 'disturb', 'stalking', 'eve teasing'],
            'intimidation': ['threaten', 'threatened', 'intimidate', 'intimidation', 'scare', 'frightened']
        }
        
        text_lower = text.lower()
        identified_offenses = []
        
        for offense_type, keywords in offense_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    identified_offenses.append(offense_type)
                    break
        
        return list(set(identified_offenses))


class DataFormatter:
    """Format data for display and export"""
    
    @staticmethod
    def format_for_display(data: Dict[str, Any]) -> str:
        """Format JSON data for readable display"""
        # Remove null values for cleaner display
        cleaned_data = DataFormatter.remove_nulls(data)
        return json.dumps(cleaned_data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def remove_nulls(data: Any) -> Any:
        """Recursively remove null values from nested dictionary"""
        if isinstance(data, dict):
            return {k: DataFormatter.remove_nulls(v) 
                   for k, v in data.items() 
                   if v is not None and v != [] and v != ""}
        elif isinstance(data, list):
            return [DataFormatter.remove_nulls(item) 
                   for item in data 
                   if item is not None]
        else:
            return data
    
    @staticmethod
    def generate_fir_number(district: str = "Unknown", year: int = None) -> str:
        """Generate a unique FIR number"""
        if year is None:
            year = datetime.now().year
        
        # Format: DISTRICT-YYYY-SEQUENTIAL
        import random
        sequential = random.randint(1000, 9999)  # In production, this would be from database
        district_code = district[:3].upper() if district else "UNK"
        
        return f"{district_code}-{year}-{sequential}"
    
    @staticmethod
    def format_datetime_display(date_str: str, time_str: str = None) -> str:
        """Format date and time for display"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted = date_obj.strftime('%d %B %Y')
            
            if time_str:
                formatted += f" at {time_str}"
            
            return formatted
        except (ValueError, TypeError):
            return f"{date_str} {time_str or ''}".strip()


class PromptTemplates:
    """Templates for LLM prompts"""
    
    @staticmethod
    def get_extraction_prompt(complaint_text: str, schema: Dict) -> str:
        """Get the extraction prompt for initial data extraction"""
        return f"""You are a police officer assistant helping to extract structured information from complaint texts.
        
Given the following complaint text, extract all relevant information and fill in the FIR schema.
For any fields you cannot determine from the text, use null.

COMPLAINT TEXT:
{complaint_text}

FIR SCHEMA TO FILL:
{json.dumps(schema, indent=2)}

EXTRACTION RULES:
1. Extract dates in YYYY-MM-DD format
2. Extract times in HH:MM format (24-hour)
3. For offense_type, choose from: theft, robbery, assault, fraud, cheating, intimidation, extortion, harassment, other
4. Extract phone numbers in 10-digit format
5. Identify all persons mentioned and their roles (complainant, victim, accused, witness)
6. Extract monetary amounts as numbers only
7. For addresses, include as much detail as available
8. Set 'is_continuing' to true if the offense is still ongoing
9. Extract any digital evidence mentioned (phone numbers, URLs, transaction IDs)
10. Keep the original complaint text in 'original_text' field

Return ONLY a valid JSON object matching the schema structure."""
    
    @staticmethod
    def get_summary_prompt(filled_data: Dict) -> str:
        """Get the prompt for generating summary"""
        return f"""Based on the following FIR data, generate a concise 5-7 line summary for police officers.
        
FIR DATA:
{json.dumps(filled_data, indent=2)}

SUMMARY REQUIREMENTS:
1. Start with complainant's name and identification
2. Describe the offense clearly and concisely  
3. Mention the date, time, and location of incident
4. Include details about the accused (if known)
5. Specify the loss/damage incurred
6. Mention any injuries or weapons involved
7. Note any available evidence or witnesses

Format as a single paragraph. Use active voice and present facts chronologically.
Do not include speculation or assumptions not present in the data."""
    
    @staticmethod
    def get_validation_prompt(partial_data: Dict, missing_info: str) -> str:
        """Get prompt for validating and filling missing information"""
        return f"""The following FIR data is missing some mandatory information.
        
CURRENT DATA:
{json.dumps(partial_data, indent=2)}

MISSING INFORMATION PROVIDED BY USER:
{missing_info}

Please update the JSON with the provided information and return the complete, validated JSON structure.
Ensure all mandatory fields are now filled."""


# Export all utility classes
__all__ = [
    'FIRValidator',
    'TextProcessor', 
    'DataFormatter',
    'PromptTemplates'
]