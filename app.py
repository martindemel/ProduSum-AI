import os
import logging
import threading
from typing import Dict, Any, Optional

import openai
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from config import AppConfig
from utils.validation import validate_form_data, sanitize_prompt_input
from utils.error_handler import handle_openai_error, log_error
from utils.cache import cache
from utils.ai_service import generate_product_description, generate_product_image_async, get_usage_stats

# Set up logging
logging.basicConfig(level=getattr(logging, AppConfig.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = AppConfig.SECRET_KEY

# Set up Socket.IO with simplified, more robust configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",     # Allow all origins (string instead of list)
    logger=True,                  # Enable logging
    engineio_logger=True,         # Enable Engine.IO logging
    ping_timeout=60,              # Standard ping timeout
    ping_interval=25,             # Standard ping interval
    async_mode='threading',       # Threading mode
    allow_upgrades=True,          # Allow transport upgrades
    cookie=False                  # No cookies for session management
)

# Check if API key exists
if not os.getenv("OPENAI_API_KEY"):
    logger.warning("OPENAI_API_KEY not found in .env or environment variables.")
    # Set a dummy key to prevent initialization errors
    os.environ["OPENAI_API_KEY"] = "dummy_key_please_set_in_env"

@app.route("/")
def index():
    """Render the main application page"""
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return f"Error loading page: {str(e)}", 500

@app.route("/health")
def health_check():
    """
    Health check endpoint for monitoring
    
    Returns basic system status information
    """
    try:
        # Check if OpenAI API key is configured
        api_configured = bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "dummy_key_please_set_in_env")
        
        # Get usage statistics
        usage = get_usage_stats()
        
        # Return health status
        return jsonify({
            "status": "ok",
            "api_configured": api_configured,
            "cache_entries": len(cache.cache),
            "usage": usage,
            "config": {
                "image_generation_enabled": AppConfig.ENABLE_IMAGE_GENERATION,
                "caching_enabled": AppConfig.ENABLE_CACHING
            }
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@socketio.on("start_generation")
def handle_generation(data):
    """
    Receives form data from client, validates it, and starts the generation process
    
    This function handles input validation, text generation, and optionally
    image generation if enabled.
    """
    try:
        logger.info(f"Received generation request from client {request.sid}")
        logger.debug(f"Generation request data: {data}")

        # Check if API key is properly configured
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "dummy_key_please_set_in_env":
            logger.error("OpenAI API key is not properly configured")
            emit("progress", {
                "data": "Error: OpenAI API key is not configured. Please check server configuration.",
                "partial": "",
                "percent": 0,
                "error": True
            })
            return
        
        # Validate the data
        is_valid, errors = validate_form_data(data)
        if not is_valid:
            logger.warning(f"Validation failed: {errors}")
            emit("progress", {
                "data": f"Error: {'; '.join(errors.values())}",
                "partial": "",
                "percent": 0,
                "errors": errors
            })
            return
            
        # Extract and sanitize fields from data
        product_name = sanitize_prompt_input(data.get("product_name", "")).strip()
        logger.info(f"Generating description for: {product_name}")
        
        # Fixed: Changed from image_toggle to generate_image to match client
        image_toggle = data.get("generate_image", False)
        
        # Check if image generation is disabled in config but requested
        if image_toggle and not AppConfig.ENABLE_IMAGE_GENERATION:
            logger.warning(f"Image generation was requested but is disabled in config")
            image_toggle = False
        
        # Store session ID for thread-safe socket emitting
        session_id = request.sid
        
        # Start image generation immediately if toggled on
        if image_toggle:
            # Start image generation in a background thread right away
            emit("progress", {
                "data": "Starting image generation in parallel...",
                "partial": "",
                "percent": 0,
                "image_generation_started": True
            })
            
            # Create a thread-safe callback for socket emissions
            def image_callback(update):
                socketio.emit("image_progress", update, room=session_id)
            
            # Start image generation in a background thread
            generate_product_image_async(
                product_name,
                image_callback,
                model=AppConfig.DEFAULT_IMAGE_MODEL
            )
            
        # Start text generation
        for progress_update in generate_product_description(
            data,
            model=AppConfig.DEFAULT_MODEL,
            use_cache=AppConfig.ENABLE_CACHING
        ):
            # Forward progress updates to the client
            emit("progress", progress_update)
            
            # If text generation is complete and image is requested but not started yet
            if progress_update.get("data") == "Text generation complete." and image_toggle and not any(k for k in progress_update if "image" in k):
                emit("progress", {
                    "data": "Text generation complete, image generation in progress.",
                    "partial": progress_update.get("partial", ""),
                    "percent": 100
                })
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in handle_generation: {str(e)}", exc_info=True)
        error_message = "An unexpected error occurred. Please try again."
        emit("progress", {
            "data": f"Error: {error_message}",
            "partial": "",
            "percent": 0,
            "error": True,
            "details": str(e)
        })

@socketio.on("connect")
def handle_connect():
    """Handle client connection"""
    logger.debug(f"Client connected: {request.sid}")
    
    # Send initial connection status to client
    emit("connection_status", {
        "status": "connected",
        "message": "Connected to server"
    })

@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    logger.debug(f"Client disconnected: {request.sid}")

@socketio.on("regenerate_image")
def handle_regenerate_image(data):
    """
    Receives product name from client and regenerates just the image
    """
    try:
        logger.info(f"Received image regeneration request from client {request.sid}")
        
        # Check if API key is properly configured
        if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "dummy_key_please_set_in_env":
            logger.error("OpenAI API key is not configured")
            emit("image_progress", {
                "status": "Error: OpenAI API key is not configured. Please check server configuration.",
                "percent": 0,
                "error": True
            })
            return
        
        # Extract product name
        product_name = sanitize_prompt_input(data.get("product_name", "")).strip()
        if not product_name:
            emit("image_progress", {
                "status": "Error: Product name is required",
                "percent": 0,
                "error": True
            })
            return
            
        logger.info(f"Regenerating image for: {product_name}")
        
        # Store session ID for thread-safe socket emitting
        session_id = request.sid
        
        # Create a thread-safe callback for socket emissions
        def image_callback(update):
            socketio.emit("image_progress", update, room=session_id)
        
        # Start image generation in a background thread
        generate_product_image_async(
            product_name,
            image_callback,
            model=AppConfig.DEFAULT_IMAGE_MODEL
        )
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in handle_regenerate_image: {str(e)}", exc_info=True)
        error_message = "An unexpected error occurred. Please try again."
        emit("image_progress", {
            "status": f"Error: {error_message}",
            "percent": 0,
            "error": True,
            "details": str(e)
        })
    
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html', error="Server error"), 500
    
if __name__ == "__main__":
    try:
        # Clean expired cache items before starting
        expired_items = cache.clean_expired()
        if expired_items > 0:
            logger.info(f"Cleaned {expired_items} expired items from cache")

        # Validate OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "dummy_key_please_set_in_env":
            logger.warning("\n" + "="*80)
            logger.warning("WARNING: No valid OpenAI API key found!")
            logger.warning("The application will start, but AI generation will not work.")
            logger.warning("Please set your OPENAI_API_KEY in the .env file.")
            logger.warning("="*80 + "\n")
        else:
            logger.info("OpenAI API key configured")
            
        # Log configuration
        logger.info(f"Starting server on {AppConfig.HOST}:{AppConfig.PORT}")
        logger.info(f"Debug mode: {AppConfig.DEBUG}")
        logger.info(f"Image generation: {'enabled' if AppConfig.ENABLE_IMAGE_GENERATION else 'disabled'}")
        logger.info(f"Caching: {'enabled' if AppConfig.ENABLE_CACHING else 'disabled'}")
        
        # Run the server
        socketio.run(
            app, 
            host=AppConfig.HOST, 
            port=AppConfig.PORT, 
            debug=AppConfig.DEBUG
        )
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        raise