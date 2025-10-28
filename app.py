"""
FIR Auto-Fill System v1.1
Streamlit application for automated complaint processing and FIR generation
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import re
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Page configuration
st.set_page_config(
    page_title="FIR Auto-Fill System",
    page_icon="📋",
    layout="wide"
)

# Load schema
def load_schema():
    """Load the FIR schema from JSON file"""
    with open('schema.json', 'r') as f:
        return json.load(f)

# Mandatory fields configuration
MANDATORY_FIELDS = {
    "complainant.name": "Complainant Name",
    "complainant.address": "Complainant Address", 
    "complainant.phone": "Phone Number",
    "incident.location.address": "Incident Location",
    "incident.datetime.occurred_on": "Incident Date",
    "offense_details.type": "Offense Type",
    "offense_details.description": "Offense Description"
}

def extract_data_from_complaint(complaint_text: str) -> Dict[str, Any]:
    """Extract structured data from complaint text using Groq LLM"""
    
    schema_str = json.dumps(load_schema(), indent=2)
    
    prompt = f"""You are a police officer assistant helping to extract structured information from complaint texts.
    
Given the following complaint text, extract all relevant information and fill in the FIR schema.
For any fields you cannot determine from the text, use null.

COMPLAINT TEXT:
{complaint_text}

FIR SCHEMA TO FILL:
{schema_str}

INSTRUCTIONS:
1. Extract dates in YYYY-MM-DD format
2. Extract times in HH:MM format  
3. For offense_type, choose from: theft, robbery, assault, fraud, cheating, intimidation, extortion, harassment, other
4. Keep original complaint text in 'original_text' field
5. Set submission_datetime to current timestamp
6. Extract phone numbers carefully
7. For unknown information, use null

Return ONLY a valid JSON object matching the schema structure. No additional text or explanations."""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a JSON extraction assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=2000
        )
        
        # Extract JSON from response
        json_str = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error extracting data: {str(e)}")
        # Return skeleton structure
        schema = load_schema()
        schema['original_text'] = complaint_text
        schema['complaint_metadata']['submission_datetime'] = datetime.now().isoformat()
        return schema

def get_nested_value(data: Dict, path: str) -> Any:
    """Get value from nested dictionary using dot notation"""
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value

def set_nested_value(data: Dict, path: str, value: Any) -> None:
    """Set value in nested dictionary using dot notation"""
    keys = path.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def validate_mandatory_fields(data: Dict) -> Dict[str, str]:
    """Check for missing mandatory fields and return dict of missing fields"""
    missing = {}
    for field_path, field_label in MANDATORY_FIELDS.items():
        value = get_nested_value(data, field_path)
        if not value or value == "null" or value == "":
            missing[field_path] = field_label
    return missing

def generate_summary(filled_data: Dict) -> str:
    """Generate a concise writer-friendly summary from the filled schema"""
    
    prompt = f"""Based on the following FIR data, generate a concise 5-7 line summary for police officers.
    
FIR DATA:
{json.dumps(filled_data, indent=2)}

INSTRUCTIONS:
Generate a brief, clear summary that captures:
1. Who the complainant is (name and basic info)
2. What happened (offense type and key facts)
3. Where and when the incident occurred
4. Against whom (if known)
5. What loss/damage occurred

Format as a readable paragraph, not bullet points. Be factual and concise."""

    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a police report summarizer. Create concise, clear summaries."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def main():
    # Header
    st.title("📋 FIR Auto-Fill System v1.1")
    st.markdown("*Automated complaint processing and structured data extraction*")
    st.divider()
    
    # Initialize session state
    if 'extracted_data' not in st.session_state:
        st.session_state.extracted_data = None
    if 'filled_data' not in st.session_state:
        st.session_state.filled_data = None
    if 'summary' not in st.session_state:
        st.session_state.summary = None
    
    # Main layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Complaint Input")
        
        # Sample complaint for testing
        sample_complaint = """I am Rajesh Kumar, residing at 45 MG Road, Bengaluru. My phone number is 9876543210.
        
On 15th January 2025 at around 8:30 PM, I was walking near the City Market area when two unknown persons on a motorcycle snatched my gold chain worth Rs. 50,000. They threatened me with a knife and fled towards the railway station. I sustained minor injuries on my neck. There were 2-3 people nearby who witnessed the incident."""
        
        complaint_text = st.text_area(
            "Enter or paste the complaint text:",
            value=sample_complaint if st.checkbox("Load sample complaint") else "",
            height=200,
            placeholder="Type or paste the complaint text here..."
        )
        
        if st.button("🚀 Extract & Process", type="primary", disabled=not complaint_text):
            if complaint_text:
                with st.spinner("Extracting structured data from complaint..."):
                    # Extract data using LLM
                    st.session_state.extracted_data = extract_data_from_complaint(complaint_text)
                    st.success("✅ Data extraction complete!")
    
    with col2:
        if st.session_state.extracted_data:
            st.subheader("📊 Extracted Data")
            
            # Check for missing mandatory fields
            missing_fields = validate_mandatory_fields(st.session_state.extracted_data)
            
            if missing_fields:
                st.warning(f"⚠️ Missing {len(missing_fields)} mandatory field(s)")
                
                # Create form for missing fields
                with st.form("missing_fields_form"):
                    st.markdown("**Please provide the following mandatory information:**")
                    
                    user_inputs = {}
                    for field_path, field_label in missing_fields.items():
                        # Special handling for different field types
                        if "date" in field_path.lower() or "occurred_on" in field_path:
                            user_inputs[field_path] = st.date_input(
                                f"{field_label} *",
                                value=datetime.now().date()
                            ).strftime("%Y-%m-%d")
                        elif "type" in field_path and "offense" in field_path:
                            user_inputs[field_path] = st.selectbox(
                                f"{field_label} *",
                                ["theft", "robbery", "assault", "fraud", "cheating", 
                                 "intimidation", "extortion", "harassment", "other"]
                            )
                        else:
                            user_inputs[field_path] = st.text_input(f"{field_label} *")
                    
                    if st.form_submit_button("✅ Submit Missing Information"):
                        # Update the extracted data with user inputs
                        for field_path, value in user_inputs.items():
                            if value:
                                set_nested_value(st.session_state.extracted_data, field_path, value)
                        
                        st.session_state.filled_data = st.session_state.extracted_data.copy()
                        st.rerun()
            else:
                st.success("✅ All mandatory fields present!")
                st.session_state.filled_data = st.session_state.extracted_data.copy()
    
    # Display results section
    if st.session_state.filled_data:
        st.divider()
        
        # Generate summary
        if not st.session_state.summary:
            with st.spinner("Generating summary..."):
                st.session_state.summary = generate_summary(st.session_state.filled_data)
        
        # Display in tabs
        tab1, tab2, tab3 = st.tabs(["🪶 Summary", "📄 Structured Data", "💾 Export"])
        
        with tab1:
            st.subheader("Writer's Summary")
            st.info(st.session_state.summary)
            
            # Key details at a glance
            st.subheader("Key Details")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Complainant", get_nested_value(st.session_state.filled_data, "complainant.name"))
                st.metric("Phone", get_nested_value(st.session_state.filled_data, "complainant.phone"))
            
            with col2:
                st.metric("Offense Type", get_nested_value(st.session_state.filled_data, "offense_details.type"))
                st.metric("Incident Date", get_nested_value(st.session_state.filled_data, "incident.datetime.occurred_on"))
            
            with col3:
                st.metric("Location", get_nested_value(st.session_state.filled_data, "incident.location.address"))
                loss_amount = get_nested_value(st.session_state.filled_data, "loss_damage.financial.total_amount")
                if loss_amount:
                    st.metric("Loss Amount", f"₹{loss_amount:,}" if loss_amount else "N/A")
        
        with tab2:
            st.subheader("Extracted Structured Data (JSON)")
            # Display JSON with syntax highlighting
            st.json(st.session_state.filled_data)
        
        with tab3:
            st.subheader("Export Options")
            
            # Download JSON
            json_str = json.dumps(st.session_state.filled_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"FIR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
            # Download Summary
            summary_content = f"""FIR SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================================

{st.session_state.summary}

=====================================
STRUCTURED DATA:
{json_str}
"""
            st.download_button(
                label="📥 Download Full Report",
                data=summary_content,
                file_name=f"FIR_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    # Sidebar with instructions
    with st.sidebar:
        st.header("📖 Instructions")
        st.markdown("""
        1. **Input Complaint**: Paste or type the complaint text
        2. **Extract Data**: Click the process button to extract structured data
        3. **Fill Missing Info**: Provide any missing mandatory information
        4. **Review Summary**: Check the auto-generated summary
        5. **Export**: Download JSON or full report
        
        ---
        
        **Mandatory Fields:**
        - Complainant name
        - Address
        - Phone number
        - Incident location
        - Incident date/time
        - Offense type/description
        
        ---
        
        **Features:**
        - 🤖 AI-powered extraction
        - ✅ Automatic validation
        - 🪶 Concise summaries
        - 💾 Export capabilities
        """)

if __name__ == "__main__":
    main()