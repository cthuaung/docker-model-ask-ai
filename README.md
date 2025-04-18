# ASK AI

A modern chat interface for interacting with AI language models.

## Features

- Clean, responsive UI with a Claude-inspired design
- Green theme and modern styling
- Markdown formatting support for responses
- Code highlighting for programming examples
- Dark/light mode toggle
- Rate limiting and caching for efficient API usage
- Environment variable configuration
- Auto-detection of various API server endpoints

## Setup with uv

This project uses `uv` for Python environment management and dependency installation for faster and more reliable setup.

1. Create project folder and set up virtual environment:

```bash
# Create project directory
mkdir ask-ai
cd ask-ai

# Create virtual environment using uv
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

2. Clone the repository and install dependencies:

```bash
# Clone the repository (or download and extract the zip)
git clone https://github.com/your-username/ask-ai.git .

# Install dependencies with uv
uv pip install -r requirements.txt
```

3. Configure environment variables (optional):

```bash
# URL of the model server (optional - the app will auto-detect the correct endpoint)
export LLM_BASE_URL="http://localhost:12434/engines/llama.cpp/v1/chat/completions"

# Or configure host and port separately
export LLM_HOST="localhost"
export LLM_PORT="12434"

# Model name to use (default: ai/smollm2)
export LLM_MODEL_NAME="ai/smollm2"

# Web server port (default: 8888)
export PORT=8888

# Debug mode (default: false)
export DEBUG=false

# Log level (default: INFO)
export LOG_LEVEL=INFO
```

4. Run the application:

```bash
python main.py
```

5. Open your browser and navigate to: http://localhost:8888

## Docker Model Runner Setup

This application has been tested with Docker Model Runner. Here's how to set it up:

1. Pull the AI model:

```bash
docker model pull ai/smollm2
```

2. Run the model:

```bash
docker model run ai/smollm2
```

The model will be accessible at http://localhost:12434 by default, which is the endpoint the ASK AI interface is configured to use.

## Server Compatibility

The app is designed to work with multiple server configurations:

- Engines format: `/engines/llama.cpp/v1/chat/completions`


The app will try to auto-detect the correct endpoint format for your server.

## Troubleshooting

If you're having trouble connecting to your model server:

1. Make sure your server is running and accessible at localhost:12434 (or your configured host:port)
2. Check that your server has the OpenAI-compatible API endpoints enabled
3. Visit http://localhost:8888/api/connection-test in your browser to get a detailed report of connection attempts
4. If a specific endpoint works, consider setting it explicitly via the LLM_BASE_URL environment variable

Common issues:

- **"Loading..." stays displayed**: The web UI cannot connect to the model server
- **No response to chat messages**: Check the logs for error messages about endpoint connections
- **Docker model not responding**: Make sure the Docker model is running correctly using `docker model ls`
- **Dependency issues**: If you have dependency issues, try `uv install --upgrade -r requirements.txt`

## Project Structure

- `main.py` - Main application file
- `requirements.txt` - Python dependencies
- `static/` - Static assets (CSS, JavaScript)
- `templates/` - HTML templates

## License

Powered by VAV
