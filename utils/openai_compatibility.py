import os
import logging
from typing import Dict, List, Any, Generator, Optional

logger = logging.getLogger(__name__)

# Check if the OpenAI package is available
try:
    import openai
    OPENAI_AVAILABLE = True
    OPENAI_VERSION = openai.__version__ if hasattr(openai, '__version__') else "unknown"
    logger.info(f"OpenAI SDK version: {OPENAI_VERSION}")
    
    # Check if version is 1.x (new client-based API) or 0.x (old style API)
    IS_NEW_API = OPENAI_VERSION.startswith("1.")
    
    if IS_NEW_API:
        logger.info("Using new OpenAI client API (v1.x)")
        # Create the client with the API key from environment
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    else:
        logger.info("Using legacy OpenAI API (v0.x)")
        # For legacy API, just set the API key
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
except ImportError:
    logger.error("OpenAI package is not installed. Please install it with: pip install openai")
    OPENAI_AVAILABLE = False
    IS_NEW_API = False

def create_chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 600,
    temperature: float = 0.7,
    stream: bool = False
) -> Any:
    """
    Compatibility wrapper for OpenAI chat completion API
    
    Works with both old-style and new client-based API
    """
    try:
        if not OPENAI_AVAILABLE:
            raise Exception("OpenAI package is not installed")
            
        if IS_NEW_API:
            # Use the new client-based API
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            return response
        else:
            # Use the old-style API
            return openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
    except Exception as e:
        logger.error(f"Error creating chat completion: {str(e)}")
        raise

def create_image(
    prompt: str,
    n: int = 1,
    size: str = "1024x1024",
    model: str = "dall-e-3",
    quality: str = "standard"
) -> Any:
    """
    Compatibility wrapper for OpenAI image generation API
    
    Works with both old-style and new client-based API
    """
    try:
        if not OPENAI_AVAILABLE:
            raise Exception("OpenAI package is not installed")
            
        if IS_NEW_API:
            # Use the new client-based API
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=n,
                size=size,
                quality=quality
            )
            return response
        else:
            # Use the old-style API
            return openai.Image.create(
                prompt=prompt,
                n=n,
                size=size,
                model=model,
                quality=quality
            )
    except Exception as e:
        logger.error(f"Error creating image: {str(e)}")
        raise

def get_completion_text(response: Any, stream: bool = False) -> str:
    """
    Extract text from completion response
    
    Works with both old-style and new client-based API response objects
    """
    if not stream:
        if IS_NEW_API:
            return response.choices[0].message.content
        else:
            return response.choices[0].message['content']
    return ""  # For streaming, handled separately

def get_image_url(response: Any) -> str:
    """
    Extract image URL from image response
    
    Works with both old-style and new client-based API response objects
    """
    if IS_NEW_API:
        return response.data[0].url
    else:
        return response['data'][0]['url']

def extract_stream_content(chunk: Any) -> Optional[str]:
    """
    Extract content from streaming response chunk
    
    Works with both old-style and new client-based API streaming formats
    """
    try:
        if IS_NEW_API:
            if hasattr(chunk.choices[0].delta, 'content'):
                return chunk.choices[0].delta.content or ""
            return ""
        else:
            return chunk.choices[0].get('delta', {}).get('content', '')
    except (AttributeError, IndexError, KeyError) as e:
        logger.warning(f"Error extracting stream content: {str(e)}")
        return "" 