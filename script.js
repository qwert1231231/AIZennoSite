// DOM Elements
const sendBtn = document.getElementById('sendBtn');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const title = document.getElementById('title');
const chatBar = document.getElementById('chatBar');
const micBtn = document.getElementById('micBtn');
const wave = document.getElementById('wave');
const newChatBtn = document.getElementById('newChatBtn');

// Chat state
let currentPersonality = 'friendly';
let isProcessing = false;

// UI Functions
function slideDownChatBar() {
    if (chatBar) chatBar.classList.add('bottomed');
    if (chatContainer) chatContainer.style.display = 'flex';
    if (title) title.style.display = 'none';
}

function addMessage(text, sender) {
    const msg = document.createElement('div');
    msg.classList.add('message', sender === 'user' ? 'user-msg' : 'ai-msg');
    msg.textContent = text;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTypingIndicator() {
    const typing = document.createElement('div');
    typing.className = 'message ai-msg typing-indicator';
    typing.innerHTML = 'AI is thinking<span>.</span><span>.</span><span>.</span>';
    chatContainer.appendChild(typing);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return typing;
}

function removeTypingIndicator(indicator) {
    if (indicator && indicator.parentNode) {
        indicator.remove();
    }
}

// API Functions
async function sendMessageToBackend(message) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                personality: currentPersonality
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        return data.response;
    } catch (error) {
        console.error('Error:', error);
        return 'Sorry, I encountered an error. Please try again.';
    }
}

// Message Handling
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || isProcessing) return;

    // Show chat container if it's the first message
    if (title.style.display !== 'none') {
        slideDownChatBar();
    }

    // Add user message
    addMessage(text, 'user');
    userInput.value = '';
    isProcessing = true;

    // Show typing indicator
    const typingIndicator = showTypingIndicator();

    try {
        // Get AI response from backend
    const response = await sendMessageToBackend(text);
    removeTypingIndicator(typingIndicator);
    addMessage(response, 'ai');
    } catch (error) {
        removeTypingIndicator(typingIndicator);
        addMessage('Sorry, I encountered an error. Please try again.', 'ai');
    } finally {
        isProcessing = false;
    }
}

// Voice Input
async function startVoiceInput() {
    try {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) throw new Error('SpeechRecognition not supported');

        const recognition = new Recognition();
        recognition.lang = 'en-US';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            if (wave) wave.style.display = 'flex';
        };

        recognition.onend = () => {
            if (wave) wave.style.display = 'none';
            // do not auto-send on end here; result handler will populate input
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            sendMessage();
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (wave) wave.style.display = 'none';
            alert('Voice input failed. Please try again or type your message.');
        };

        recognition.start();
    } catch (error) {
        alert('Voice input is not supported in your browser. Please type your message instead.');
    }
}

// Event Listeners (guarded so script can be loaded on other pages like index.html)
if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
}

if (userInput) {
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

if (micBtn) {
    micBtn.addEventListener('click', startVoiceInput);
}

if (newChatBtn) {
    newChatBtn.addEventListener('click', () => {
        if (chatContainer) chatContainer.innerHTML = '';
        if (title) title.style.display = 'block';
        if (chatBar) chatBar.style.animation = 'slideToMiddle 0.8s ease forwards';
    });
}

// Get Started button: go to chat if logged in, otherwise to signup
const getStartedBtn = document.getElementById('getStarted');
if (getStartedBtn) {
    getStartedBtn.addEventListener('click', () => {
        const u = localStorage.getItem('aizeeno_user');
        if (u) {
            window.location.href = 'chat/chat.html';
        } else {
            window.location.href = 'auth/signup.html';
        }
    });
}

// Initialize chat session
async function initChat() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/chat/init', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to initialize chat session');
        }
        
        const data = await response.json();
        currentPersonality = data.defaultPersonality || 'friendly';
    } catch (error) {
        console.error('Error initializing chat:', error);
    }
}

// Start initialization when page loads
document.addEventListener('DOMContentLoaded', initChat);

// Conversations sidebar and saving removed for now (keeps backend endpoints intact)

// Rotating Title Text (moved from chat.html)
;(function setupRotatingTitle(){
        const phrases = [
            "What can I help with?",
            "What can I assist you with?",
            "How can I support you today?",
            "Need help with something?"
        ];
        let idx = 0;
        setInterval(() => {
            idx = (idx + 1) % phrases.length;
            title.style.opacity = 0;
            setTimeout(() => {
                title.textContent = phrases[idx];
                title.style.opacity = 1;
            }, 500);
        }, 4000);
})();

// Wave element handling exists; the voice flow updates wave display from startVoiceInput
