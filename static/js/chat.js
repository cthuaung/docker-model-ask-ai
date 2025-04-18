document.addEventListener('DOMContentLoaded', function() {
    console.log("Chat interface initializing...");
    
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const sendButton = document.getElementById('send-button');
    const modelNameElement = document.getElementById('model-name');
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    
    // Check that all elements were found
    if (!chatForm) console.error("Chat form not found!");
    if (!userInput) console.error("User input not found!");
    if (!chatMessages) console.error("Chat messages container not found!");
    if (!sendButton) console.error("Send button not found!");
    if (!modelNameElement) console.error("Model name element not found!");
    if (!darkModeToggle) console.error("Dark mode toggle not found!");
    
    console.log("DOM elements initialized");
    
    // Auto-resize textarea
    function autoResizeTextarea() {
        // Reset height to auto to get the correct scrollHeight
        userInput.style.height = 'auto';
        // Set to scrollHeight but limit to max height defined in CSS
        userInput.style.height = Math.min(userInput.scrollHeight, 200) + 'px';
    }
    
    // Initialize the textarea height
    autoResizeTextarea();
    
    // Add input event listener for auto-resizing
    userInput.addEventListener('input', autoResizeTextarea);
    
    // Check for saved theme preference or use default
    const savedTheme = localStorage.getItem('theme') || 'light';
    console.log("Saved theme:", savedTheme);
    applyTheme(savedTheme);
    
    // Set up marked.js for markdown rendering
    if (typeof marked !== 'undefined') {
        console.log("Setting up marked.js");
        marked.setOptions({
            highlight: function(code, lang) {
                if (typeof hljs !== 'undefined') {
                    if (lang && hljs.getLanguage(lang)) {
                        return hljs.highlight(code, { language: lang }).value;
                    } else {
                        return hljs.highlightAuto(code).value;
                    }
                }
                return code;
            },
            breaks: true
        });
    } else {
        console.error("marked.js is not loaded!");
    }
    
    // Get model info and test connection
    console.log("Starting model info fetch");
    fetchModelInfo();
    
    // Event listeners
    console.log("Setting up event listeners");
    chatForm.addEventListener('submit', handleChatSubmit);
    userInput.addEventListener('keydown', handleKeyDown);
    darkModeToggle.addEventListener('change', handleThemeChange);
    
    // Automatically focus the input field
    userInput.focus();
    
    // Helper functions
    function handleChatSubmit(e) {
        e.preventDefault();
        console.log("Form submitted");
        const message = userInput.value.trim();
        
        if (message) {
            console.log("Sending message:", message);
            // Add user message to chat
            addMessageToChat('user', message);
            
            // Clear input field and reset height
            userInput.value = '';
            userInput.style.height = 'auto';
            
            // Show typing indicator
            showTypingIndicator();
            
            // Disable send button while processing
            sendButton.disabled = true;
            
            // Send message to server
            sendMessageToServer(message);
        } else {
            console.log("Empty message, not sending");
        }
    }
    
    function handleKeyDown(e) {
        // Send on Shift+Enter
        if (e.key === 'Enter' && e.shiftKey) {
            console.log("Shift+Enter pressed");
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    }
    
    function handleThemeChange() {
        console.log("Theme change triggered");
        const newTheme = darkModeToggle.checked ? 'dark' : 'light';
        console.log("Setting theme to:", newTheme);
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
    }
    
    function applyTheme(theme) {
        console.log("Applying theme:", theme);
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            darkModeToggle.checked = true;
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            darkModeToggle.checked = false;
        }
    }
    
    function addMessageToChat(role, content) {
        console.log(`Adding ${role} message to chat`);
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Safely render the content
        if (role === 'assistant') {
            // Use marked for markdown rendering with sanitization
            if (typeof marked !== 'undefined') {
                console.log("Rendering markdown");
                messageContent.innerHTML = marked.parse(content);
                
                // Apply syntax highlighting to code blocks
                if (typeof hljs !== 'undefined') {
                    messageContent.querySelectorAll('pre code').forEach(block => {
                        hljs.highlightBlock(block);
                    });
                }
            } else {
                console.error("marked.js not available, falling back to text content");
                messageContent.textContent = content;
            }
        } else {
            // Simple text content for user messages
            messageContent.textContent = content;
        }
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function showTypingIndicator() {
        console.log("Showing typing indicator");
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            typingDiv.appendChild(dot);
        }
        
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function hideTypingIndicator() {
        console.log("Hiding typing indicator");
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        } else {
            console.warn("Typing indicator not found");
        }
    }
    
    function sendMessageToServer(message) {
        console.log("Sending message to server");
        
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            console.log("Server response received:", response.status);
            if (!response.ok) {
                return response.json().then(errData => {
                    console.error("Error response data:", errData);
                    throw new Error(errData.error || `Server responded with status: ${response.status}`);
                }).catch(err => {
                    if (err instanceof SyntaxError) {
                        // If the response is not JSON, just throw the status
                        console.error("Non-JSON error response");
                        throw new Error(`Server responded with status: ${response.status}`);
                    }
                    throw err;
                });
            }
            return response.json();
        })
        .then(data => {
            console.log("Response data received:", data);
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Display the response
            if (data.response) {
                console.log("Displaying assistant response");
                addMessageToChat('assistant', data.response);
            } else if (data.error) {
                console.error("Server reported error:", data.error);
                addSystemMessage(`Error: ${data.error}`);
            } else {
                console.error("Empty response data:", data);
                addSystemMessage('Received empty response from server');
            }
            
            // Re-enable send button
            sendButton.disabled = false;
            
            // Focus input field again
            userInput.focus();
        })
        .catch(error => {
            console.error("Request failed:", error);
            
            // Hide typing indicator
            hideTypingIndicator();
            
            // Show detailed error message
            addSystemMessage(`Error: Could not get a response from the server. ${error.message}. Please check that your LLaMA.cpp server is running at the correct URL.`);
            
            // Re-enable send button
            sendButton.disabled = false;
        });
    }
    
    function addSystemMessage(message) {
        console.log("Adding system message:", message);
        const systemDiv = document.createElement('div');
        systemDiv.className = 'system-message';
        
        // Check if the message contains HTML
        if (message.includes('<') && message.includes('>')) {
            systemDiv.innerHTML = message;
        } else {
            systemDiv.textContent = message;
        }
        
        chatMessages.appendChild(systemDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    function fetchModelInfo() {
        console.log("Fetching model info");
        modelNameElement.textContent = "Checking connection...";
        
        // First test the connection
        testConnection()
            .then(connectionResult => {
                console.log("Connection test result:", connectionResult);
                if (connectionResult.status === 'ok') {
                    // Connection is good, get model info
                    console.log("Connection OK, fetching model info");
                    return fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ message: '!modelinfo' })
                    })
                    .then(response => {
                        console.log("Model info response:", response.status);
                        if (!response.ok) {
                            throw new Error(`Server responded with status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log("Model info data:", data);
                        if (data.model) {
                            modelNameElement.textContent = data.model;
                            return { success: true };
                        } else if (data.error) {
                            modelNameElement.textContent = 'Error: ' + data.error;
                            return { success: false, error: data.error };
                        } else {
                            modelNameElement.textContent = 'Unknown model';
                            return { success: false, error: 'Unknown model' };
                        }
                    });
                } else {
                    // Connection failed
                    console.error("Connection failed");
                    modelNameElement.textContent = 'Connection failed';
                    throw new Error(connectionResult.message || 'Failed to connect to LLaMA.cpp server');
                }
            })
            .catch(error => {
                console.error('Error fetching model info:', error);
                modelNameElement.textContent = 'Connection failed';
                
                // Show detailed connection error to the user
                const errorMsg = `
Could not connect to the LLaMA.cpp server. Please check:

1. Is your LLaMA.cpp server running?
2. Is it running on the correct port (default: 12434)?
3. Is it using the OpenAI-compatible API endpoint?

Try accessing the connection test page for more details:
<a href="/api/connection-test" target="_blank">Test Connection</a>

Error: ${error.message}
`;
                
                addSystemMessage(errorMsg);
            });
    }
    
    function testConnection() {
        console.log("Testing connection to server");
        return fetch('/api/connection-test')
            .then(response => {
                console.log("Connection test response:", response.status);
                return response.json();
            })
            .then(data => {
                console.log("Connection test data:", data);
                return data;
            })
            .catch(error => {
                console.error("Connection test error:", error);
                return {
                    status: 'error',
                    message: 'Could not connect to the web server: ' + error.message
                };
            });
    }
    
    // Log initialization complete
    console.log("Chat interface initialization complete");
}); 