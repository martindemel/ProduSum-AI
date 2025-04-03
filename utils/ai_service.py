import os
import time
import threading
import logging
from typing import Dict, Any, Optional, List, Callable, Generator

try:
    # Import our compatibility layer instead of directly using OpenAI
    from .openai_compatibility import (
        create_chat_completion,
        create_image,
        extract_stream_content,
        get_image_url,
        IS_NEW_API,
        OPENAI_AVAILABLE
    )
    if not OPENAI_AVAILABLE:
        print("ERROR: OpenAI module not found. Please install with: pip install openai")
except ImportError as e:
    print(f"ERROR: Failed to import OpenAI compatibility layer: {e}")
    OPENAI_AVAILABLE = False

from .cache import cache
from .validation import sanitize_prompt_input
from .error_handler import handle_openai_error

logger = logging.getLogger(__name__)

# Track usage stats
usage_stats = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_images": 0,
    "last_reset": time.time()
}

def reset_usage_stats() -> None:
    """Reset the usage statistics"""
    global usage_stats
    usage_stats = {
        "total_requests": 0,
        "total_tokens": 0,
        "total_images": 0,
        "last_reset": time.time()
    }

def get_usage_stats() -> Dict[str, Any]:
    """Get the current usage statistics"""
    return usage_stats

def generate_product_description(
    product_info: Dict[str, Any],
    model: str = "gpt-4",
    max_tokens: int = 600,
    temperature: float = 0.7,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = True
) -> Generator[Dict[str, Any], None, None]:
    """
    Generate a product description using OpenAI
    
    Args:
        product_info: Dictionary containing product details
        model: The OpenAI model to use
        max_tokens: Maximum tokens to generate
        temperature: Temperature for generation (0.0-1.0)
        stream_callback: Optional callback for streaming responses
        use_cache: Whether to use caching
        
    Yields:
        Dictionary with generation progress updates
    """
    global usage_stats
    
    # Clean and sanitize inputs
    product_name = sanitize_prompt_input(product_info.get("product_name", ""))
    product_details = sanitize_prompt_input(product_info.get("product_details", ""))
    language = sanitize_prompt_input(product_info.get("language", "English"))
    tone = sanitize_prompt_input(product_info.get("tone", "Professional"))
    keywords = sanitize_prompt_input(product_info.get("keywords", ""))
    audience = sanitize_prompt_input(product_info.get("audience", ""))
    platform = sanitize_prompt_input(product_info.get("platform", ""))
    usps = sanitize_prompt_input(product_info.get("usps", ""))
    cta_style = sanitize_prompt_input(product_info.get("cta_style", ""))
    viral_flag = product_info.get("viral") == "Yes"
    extra_instructions = sanitize_prompt_input(product_info.get("extra_instructions", ""))
    
    # Check cache if enabled
    if use_cache:
        cache_key = cache.create_key(
            "product_description",
            product_name=product_name,
            product_details=product_details,
            language=language,
            tone=tone,
            keywords=keywords,
            audience=audience,
            platform=platform,
            usps=usps,
            cta_style=cta_style,
            viral_flag=viral_flag,
            extra_instructions=extra_instructions,
            model=model
        )
        
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.info(f"Using cached description for '{product_name}'")
            yield {
                "data": "Using cached result...",
                "partial": "",
                "percent": 50
            }
            yield {
                "data": "Text generation complete.",
                "partial": cached_result,
                "percent": 100
            }
            return
    
    # Build prompt
    system_message = (
        "You are an advanced marketing copywriter assistant specializing in compelling product descriptions. "
        "Follow the user instructions precisely and format your response into labeled sections. "
        "Ensure the Body section always has at least one substantial paragraph with engaging content. "
        "Use persuasive language and focus on benefits rather than just features."
    )
    
    prompt_lines = []
    prompt_lines.append(f"Product Name: {product_name}")
    
    if product_details:
        prompt_lines.append(f"Product Details: {product_details}")
    if language:
        prompt_lines.append(f"Language: {language}")
    if tone:
        prompt_lines.append(f"Tone: {tone}")
    if keywords:
        prompt_lines.append(f"SEO Keywords: {keywords}")
    if audience:
        prompt_lines.append(f"Target Audience: {audience}")
    if platform:
        prompt_lines.append(f"Platform: {platform}")
    if usps:
        prompt_lines.append(f"Unique Selling Points: {usps}")
    if cta_style:
        prompt_lines.append(f"CTA Style: {cta_style}")
        
    if viral_flag:
        prompt_lines.append("Include emotional triggers, social proof, and FOMO for a viral effect.")
    else:
        prompt_lines.append("Avoid explicit FOMO or hype; keep it persuasive yet balanced.")

    instructions = (
        "Write a compelling product description with these labeled sections:\n"
        "Hook: (A short, attention-grabbing opening line)\n"
        "Body: (At least one full paragraph describing benefits and features)\n"
        "CTA: (A clear call-to-action)\n\n"
        "Then provide a line labeled 'Suggested Hashtags and Keywords:' at the end. "
        "Make sure each section is clearly marked."
    )
    
    if extra_instructions.strip():
        instructions += f"\nAdditional instructions:\n{extra_instructions.strip()}"

    prompt_context = "\n".join(prompt_lines)
    final_prompt = f"{prompt_context}\n\n{instructions}"

    # Track request
    usage_stats["total_requests"] += 1
    
    # Generate the text
    output_text = ""
    try:
        yield {"data": "Generating product description...", "partial": ""}
        
        # Create messages array for API call
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": final_prompt}
        ]
        
        # Use our compatibility wrapper instead of direct API call
        response = create_chat_completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        # Stream partial tokens
        total_tokens = 0
        
        for chunk in response:
            # Use compatibility function to extract content from chunk
            delta = extract_stream_content(chunk)
            
            if delta:
                output_text += delta
                total_tokens += 1
                # Calculate progress
                percent = min(100, int((total_tokens / 300) * 100))
                yield {
                    "data": "Generating description...",
                    "partial": output_text,
                    "percent": percent
                }
                
                # Call stream callback if provided
                if stream_callback:
                    stream_callback(delta)
        
        # Update token usage stats
        usage_stats["total_tokens"] += total_tokens
        
        # Store in cache if successful
        if use_cache:
            cache.set(cache_key, output_text)
            
        # Text generation complete
        yield {
            "data": "Text generation complete.",
            "partial": output_text,
            "percent": 100
        }
        
    except Exception as e:
        error_msg, error_details = handle_openai_error(e)
        logger.error(f"Error generating description: {error_msg}", exc_info=True)
        yield {
            "data": f"Error: {error_msg}",
            "partial": output_text if output_text else "",
            "percent": 0,
            "error": True,
            "error_details": error_details
        }

def generate_product_image_async(
    product_name: str,
    callback: Callable[[Dict[str, Any]], None],
    model: str = "dall-e-3",
    size: str = "1024x1024",
    quality: str = "standard"
) -> None:
    """
    Generate a product image asynchronously with DALL-E
    
    Args:
        product_name: The name of the product
        callback: Callback function to receive image updates
        model: The DALL-E model to use
        size: Image size
        quality: Image quality
    """
    # Make a local copy of all parameters to prevent scoping issues
    local_product_name = product_name
    local_callback = callback
    local_model = model
    local_size = size
    local_quality = quality
    
    def _generate_image():
        global usage_stats
        
        try:
            # Clean input
            sanitized_product_name = sanitize_prompt_input(local_product_name)
            
            # Step 1: Creating image prompt
            local_callback({
                "status": "Creating image prompt...",
                "percent": 10
            })
            
            # Check cache
            cache_key = cache.create_key(
                "product_image",
                product_name=sanitized_product_name,
                model=local_model,
                size=local_size,
                quality=local_quality
            )
            
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Using cached image for '{sanitized_product_name}'")
                local_callback({
                    "status": "Using cached image...",
                    "percent": 50
                })
                # Send image URL without success message
                local_callback({
                    "percent": 100,
                    "image_url": cached_result
                })
                return
            
            # Create the image prompt
            image_prompt = f"Generate a realistic, high-quality image of the product: {sanitized_product_name}. Do not include any text, logos, or branding."
            
            # Step 2: Sending to DALL-E
            local_callback({
                "status": "Sending request to DALL-E 3...",
                "percent": 25
            })
            
            # Step 3: Generate the image
            local_callback({
                "status": "Your image is being generated, it can take up to 30 seconds...",
                "percent": 50
            })
            
            # Track image generation
            usage_stats["total_images"] += 1
            usage_stats["total_requests"] += 1
            
            # Generate the image using compatibility wrapper
            image_response = create_image(
                prompt=image_prompt,
                n=1,
                size=local_size,
                model=local_model,
                quality=local_quality
            )
            
            # Get image URL using compatibility function
            image_url = get_image_url(image_response)
            
            # Cache the result
            cache.set(cache_key, image_url)
            
            # Send only the URL and percent without status message
            local_callback({
                "percent": 100,
                "image_url": image_url
            })
            
        except Exception as e:
            error_msg, error_details = handle_openai_error(e)
            logger.error(f"Image generation error: {error_msg}", exc_info=True)
            
            local_callback({
                "status": f"Image generation failed: {error_msg}",
                "percent": 100,
                "error": True,
                "error_details": error_details
            })
    
    # Run in background thread to avoid blocking
    thread = threading.Thread(target=_generate_image)
    thread.daemon = True
    thread.start()
    
    return thread 