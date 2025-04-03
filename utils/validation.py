import re
from typing import Tuple, Dict, Any

def sanitize_prompt_input(text: str) -> str:
    """
    Sanitize user input to prevent prompt injection attacks
    
    This function removes control characters, markdown code blocks,
    and attempts to override system/user role prompts
    """
    if not text:
        return ""
        
    # Remove any markdown code block syntax
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Remove any attempt to use system/user role prompts
    text = re.sub(r'(system:|user:|assistant:)', '', text, flags=re.IGNORECASE)
    
    # Remove any instructions to ignore previous instructions
    text = re.sub(r'ignore previous instructions', '', text, flags=re.IGNORECASE)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def validate_product_name(name: str) -> Tuple[bool, str]:
    """Validate the product name"""
    if not name or not name.strip():
        return False, "Product name is required"
    if len(name) > 100:
        return False, "Product name must be under 100 characters"
    return True, ""

def validate_product_details(details: str) -> Tuple[bool, str]:
    """Validate the product details"""
    if len(details) > 1000:
        return False, "Product details must be under 1000 characters"
    return True, ""

def validate_keywords(keywords: str) -> Tuple[bool, str]:
    """Validate the SEO keywords"""
    if len(keywords) > 200:
        return False, "Keywords must be under 200 characters"
    return True, ""

def validate_extra_instructions(instructions: str) -> Tuple[bool, str]:
    """Validate the extra instructions"""
    if len(instructions) > 500:
        return False, "Extra instructions must be under 500 characters"
    return True, ""

def validate_form_data(data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
    """
    Validate all form data
    
    Returns:
        Tuple[bool, Dict[str, str]]: (is_valid, error_messages)
    """
    errors = {}
    
    # Validate product name (required)
    valid, message = validate_product_name(data.get("product_name", ""))
    if not valid:
        errors["product_name"] = message
        
    # Validate other fields (optional)
    for field, validator in [
        ("product_details", validate_product_details),
        ("keywords", validate_keywords),
        ("extra_instructions", validate_extra_instructions)
    ]:
        if field in data and data[field]:
            valid, message = validator(data.get(field, ""))
            if not valid:
                errors[field] = message
                
    return len(errors) == 0, errors 