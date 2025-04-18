import os
import json
import datetime
import logging
import sys

# Check for required dependencies
try:
    import requests
    from flask import Flask, render_template, request, jsonify, make_response, url_for
    from flask_caching import Cache
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError as e:
    print(f"Error: Missing required dependency - {e}")
    print("Please install all required dependencies using: pip install -r requirements.txt")
    sys.exit(1)

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Configure cache
cache_config = {
    "CACHE_TYPE": "SimpleCache",  # Simple in-memory cache
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutes
}
cache = Cache(app, config=cache_config)

# Configure rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def configure_logging():
    """Configure application logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    # Configure Flask logger
    app.logger.setLevel(numeric_level)
    # Add a formatter to the handler
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    for handler in app.logger.handlers:
        handler.setFormatter(formatter)

# Server connection settings
# These functions handle the connection to your local model server

def get_llm_endpoint():
    """Returns the complete LLM API endpoint URL"""
    # If LLM_BASE_URL is set explicitly, use that
    base_url = os.getenv("LLM_BASE_URL")
    if base_url:
        return base_url
    
    # Otherwise construct from host and port
    host = os.getenv("LLM_HOST", "localhost")
    port = os.getenv("LLM_PORT", "12434")
    
    # Return the engines format endpoint which is known to work with the user's setup
    return f"http://{host}:{port}/engines/llama.cpp/v1/chat/completions"

def get_alternative_endpoints():
    """Returns a list of alternative endpoints to try if the main one fails"""
    host = os.getenv("LLM_HOST", "localhost")
    port = os.getenv("LLM_PORT", "12434")
    
    return [
        # Original format with engines prefix (used by some variants)
        f"http://{host}:{port}/engines/llama.cpp/v1/chat/completions",
        # Standard OpenAI format
        f"http://{host}:{port}/v1/chat/completions",
        # Default for some servers
        f"http://{host}:{port}/chat/completions",
        # Local AI style endpoint
        f"http://{host}:{port}/api/chat"
    ]

def get_model_name():
    """Returns the model name to use for API requests"""
    return os.getenv("LLM_MODEL_NAME", "ai/smollm2")

@app.route('/')
def index():
    """Serves the chat web interface"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for container orchestration"""
    # Check if LLM API is accessible
    llm_status = "ok"
    try:
        # Simple check if the LLM endpoint is configured
        if not get_llm_endpoint():
            llm_status = "not_configured"
    except Exception as e:
        llm_status = "error"
        app.logger.error(f"Health check error: {e}")

    return jsonify({
        "status": "healthy",
        "llm_api": llm_status,
        "timestamp": datetime.datetime.now().isoformat()
    })

def validate_chat_request(data):
    """Validates and sanitizes chat API request data"""
    if not isinstance(data, dict):
        return False, "Invalid request format"
    
    message = data.get('message', '')
    if not message or not isinstance(message, str):
        return False, "Message is required and must be a string"
    
    if len(message) > 4000:  # Reasonable limit
        return False, "Message too long (max 4000 characters)"
    
    return True, message

@app.route('/api/chat', methods=['POST'])
@limiter.limit("10 per minute")
def chat_api():
    """Processes chat API requests"""
    app.logger.info("Received chat API request")
    
    try:
        data = request.json
        app.logger.debug(f"Request data: {data}")
        
        # Validate request
        valid, result = validate_chat_request(data)
        if not valid:
            app.logger.warning(f"Invalid request: {result}")
            return jsonify({'error': result}), 400
        
        message = result
        app.logger.info(f"Processing message (length: {len(message)})")
        
        # Special command for getting model info
        if message == "!modelinfo":
            app.logger.info("Handling modelinfo request")
            return jsonify({'model': get_model_name()})
        
        # Call the LLM API
        try:
            app.logger.info("Calling LLM API")
            response = call_llm_api(message)
            app.logger.info(f"Got LLM response (length: {len(response)})")
            return jsonify({'response': response})
        except Exception as e:
            app.logger.error(f"Error calling LLM API: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to get response from LLM: {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in chat_api: {str(e)}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@cache.memoize(timeout=300)
def call_llm_api(user_message):
    """Calls the LLM API and returns the response with caching"""
    # Get the main endpoint and alternatives
    main_endpoint = get_llm_endpoint()
    
    headers = {"Content-Type": "application/json"}
    
    # Construct the payload in the format expected by LLaMA.cpp server
    payload = {
        "model": get_model_name(),
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Please provide structured responses using markdown formatting."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        # Add these optional parameters which can help with certain LLaMA.cpp servers
        "stream": False,  # We don't want streaming for this application
        "max_tokens": 2000,  # Reasonable limit for responses
        "temperature": 0.7  # Standard creative temperature
    }
    
    # Log request information
    app.logger.info(f"Sending request to LLM API at: {main_endpoint}")
    app.logger.info(f"Using model: {get_model_name()}")
    app.logger.debug(f"Payload: {payload}")
    
    # Try the main endpoint first
    try:
        # Send request to LLM API
        response = requests.post(
            main_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        # Log response status
        app.logger.info(f"LLM API response status: {response.status_code}")
        
        # Check if the status code is not 200 OK
        if response.status_code != 200:
            # If the main endpoint failed, let's try alternatives
            app.logger.warning(f"Main endpoint failed with status {response.status_code}, trying alternatives")
            app.logger.debug(f"Response content: {response.text[:500]}")
            return try_alternative_endpoints(user_message)
        
        # Parse the response
        chat_response = response.json()
        app.logger.info("Successfully received response from LLM API")
        app.logger.debug(f"Raw response: {chat_response}")
        
        # Extract the assistant's message
        if chat_response.get('choices') and len(chat_response['choices']) > 0:
            content = chat_response['choices'][0]['message']['content'].strip()
            return content
        
        app.logger.error("No response choices returned from API")
        app.logger.debug(f"Full response: {chat_response}")
        raise Exception("No response choices returned from API")
    
    except requests.exceptions.ConnectionError as e:
        app.logger.warning(f"Connection error with main endpoint: {e}, trying alternatives")
        return try_alternative_endpoints(user_message)
    except requests.exceptions.Timeout as e:
        app.logger.warning(f"Timeout with main endpoint: {e}, trying alternatives")
        return try_alternative_endpoints(user_message)
    except Exception as e:
        app.logger.error(f"Unexpected error with main endpoint: {e}")
        app.logger.debug(f"Error details: {str(e)}", exc_info=True)
        
        # Only try alternatives for certain errors
        if "connection" in str(e).lower() or "timeout" in str(e).lower():
            return try_alternative_endpoints(user_message)
        raise

def try_alternative_endpoints(user_message):
    """Try alternative endpoints if the main one fails"""
    alternative_endpoints = get_alternative_endpoints()
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": get_model_name(),
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Please provide structured responses using markdown formatting."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        # Add these optional parameters which can help with certain LLaMA.cpp servers
        "stream": False,
        "max_tokens": 2000,
        "temperature": 0.7
    }
    
    # Try each alternative endpoint
    for endpoint in alternative_endpoints:
        try:
            app.logger.info(f"Trying alternative endpoint: {endpoint}")
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                app.logger.info(f"Alternative endpoint {endpoint} succeeded")
                
                # Parse the response
                chat_response = response.json()
                app.logger.debug(f"Raw response from alternative endpoint: {chat_response}")
                
                # Extract the assistant's message
                if chat_response.get('choices') and len(chat_response['choices']) > 0:
                    content = chat_response['choices'][0]['message']['content'].strip()
                    return content
                
                app.logger.error(f"No response choices from alternative endpoint {endpoint}")
            else:
                app.logger.warning(f"Alternative endpoint {endpoint} failed with status {response.status_code}")
                app.logger.debug(f"Response content: {response.text[:500]}")
        
        except Exception as e:
            app.logger.warning(f"Error with alternative endpoint {endpoint}: {e}")
    
    # If we get here, all endpoints failed
    raise Exception("Failed to connect to any LLaMA.cpp server endpoint. Please check your LLaMA.cpp server configuration.")

@app.after_request
def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com"
    return response

@app.route('/api/connection-test')
def test_connection():
    """Tests the connection to the LLaMA.cpp server by trying multiple endpoint formats"""
    
    # Get the main endpoint and alternatives
    main_endpoint = get_llm_endpoint()
    alternative_endpoints = get_alternative_endpoints()
    
    # Combine all endpoints, ensuring no duplicates
    all_endpoints = [main_endpoint]
    for endpoint in alternative_endpoints:
        if endpoint not in all_endpoints:
            all_endpoints.append(endpoint)
    
    # Basic result info
    result = {
        "endpoints_tested": all_endpoints,
        "model": get_model_name(),
        "time": datetime.datetime.now().isoformat(),
        "status": "error",
        "message": "Failed to connect to any endpoint",
        "endpoint_results": {}
    }
    
    # Try each endpoint
    for endpoint in all_endpoints:
        endpoint_result = {
            "status": "unknown",
            "message": ""
        }
        
        try:
            # Try a minimal POST request to the chat completions endpoint
            app.logger.info(f"Testing endpoint: {endpoint}")
            response = requests.post(
                endpoint,
                headers={"Content-Type": "application/json"},
                json={
                    "model": get_model_name(),
                    "messages": [
                        {
                            "role": "user",
                            "content": "test"
                        }
                    ]
                },
                timeout=5
            )
            
            endpoint_result["status_code"] = response.status_code
            
            if response.status_code == 200:
                endpoint_result["status"] = "ok"
                endpoint_result["message"] = "Connection successful"
                
                # If this is the first successful endpoint, update the main result
                if result["status"] != "ok":
                    result["status"] = "ok"
                    result["message"] = f"Successfully connected to {endpoint}"
                    result["working_endpoint"] = endpoint
                    
                    # If this isn't the main endpoint, suggest updating the config
                    if endpoint != main_endpoint:
                        result["suggestion"] = f"Consider setting LLM_BASE_URL={endpoint} for faster connections"
            else:
                endpoint_result["status"] = "error"
                endpoint_result["message"] = f"Server responded with status code: {response.status_code}"
                endpoint_result["response_text"] = response.text[:200]  # Limit response text
        
        except requests.exceptions.ConnectionError as e:
            endpoint_result["status"] = "error"
            endpoint_result["message"] = f"Connection error"
            endpoint_result["error"] = str(e)
        except requests.exceptions.Timeout as e:
            endpoint_result["status"] = "error"
            endpoint_result["message"] = "Connection timed out"
            endpoint_result["error"] = str(e)
        except Exception as e:
            endpoint_result["status"] = "error"
            endpoint_result["message"] = "Unexpected error"
            endpoint_result["error"] = str(e)
        
        # Add this endpoint's result to the main result
        result["endpoint_results"][endpoint] = endpoint_result
    
    # Return complete test results
    return jsonify(result)

def check_llm_connection():
    """Checks the connection to the LLaMA.cpp server at startup and logs the result"""
    endpoint = get_llm_endpoint()
    app.logger.info(f"Checking connection to LLaMA.cpp server at: {endpoint}")
    
    try:
        # Make a simple request to check connection
        response = requests.post(
            endpoint,
            headers={"Content-Type": "application/json"},
            json={
                "model": get_model_name(),
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5,
                "temperature": 0.0
            },
            timeout=10
        )
        
        if response.status_code == 200:
            app.logger.info("✅ Successfully connected to LLaMA.cpp server")
            return True
        else:
            app.logger.warning(f"⚠️ LLaMA.cpp server responded with status code: {response.status_code}")
            app.logger.warning(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        app.logger.warning(f"⚠️ Could not connect to LLaMA.cpp server: {e}")
        return False

if __name__ == '__main__':
    # Configure logging
    configure_logging()
    
    # Validate environment
    port = int(os.getenv("PORT", 8888))
    
    app.logger.info(f"Server starting on http://localhost:{port}")
    app.logger.info(f"Using LLM endpoint: {get_llm_endpoint()}")
    app.logger.info(f"Using model: {get_model_name()}")
    
    # Check LLM connection on startup
    if not check_llm_connection():
        app.logger.warning("⚠️ Could not connect to LLaMA.cpp server at startup")
        app.logger.warning("⚠️ Chat functionality may not work until the LLaMA.cpp server is available")
        app.logger.warning("⚠️ You can visit /api/connection-test in your browser for more details")
    
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
