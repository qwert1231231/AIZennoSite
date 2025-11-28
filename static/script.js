// ------------------------
// DOM ELEMENTS
// ------------------------
const sendBtn = document.getElementById('sendBtn');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const title = document.getElementById('title');
const chatBar = document.getElementById('chatBar');
const micBtn = document.getElementById('micBtn');
const wave = document.getElementById('wave');
const newChatBtn = document.getElementById('newChatBtn');
const plusPopup = document.getElementById('plusPopup');
const closePopup = document.getElementById('closePopup');
const upgradeBtn = document.getElementById('upgradeBtn');
const getStartedBtn = document.getElementById('getStarted');
const closeUpgrade = document.getElementById('closeUpgrade');

// Backend base for API calls (frontend may be served on a different port)
const BACKEND_BASE = 'http://127.0.0.1:5000';

// ------------------------
// CHAT STATE
// ------------------------
let currentPersonality = 'friendly';
let isProcessing = false;

// ------------------------
// UI HELPERS
// ------------------------
function slideDownChatBar() {
    chatBar?.classList.add('bottomed');
    chatContainer && (chatContainer.style.display = 'flex');
    title && (title.style.display = 'none');
}

function addMessage(text, sender) {
    if (!chatContainer) return;
    const msg = document.createElement('div');
    msg.classList.add('message', sender === 'user' ? 'user-msg' : 'ai-msg');
    msg.textContent = text;
    chatContainer.appendChild(msg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTypingIndicator() {
    if (!chatContainer) return null;
    const typing = document.createElement('div');
    typing.className = 'message ai-msg typing-indicator';
    typing.innerHTML = 'AI is thinking<span>.</span><span>.</span><span>.</span>';
    chatContainer.appendChild(typing);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return typing;
}

function removeTypingIndicator(indicator) {
    indicator?.remove();
}

// ------------------------
// API FUNCTIONS
// ------------------------
async function sendMessageToBackend(message) {
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data.response || 'No response received';
    } catch (error) {
        console.error('Chat API Error:', error);
        return 'Sorry, I encountered an error. Please try again.';
    }
}

// ------------------------
// MESSAGE HANDLING
// ------------------------
async function sendMessage() {
    const text = userInput?.value.trim();
    if (!text || isProcessing) return;

    if (title && title.style.display !== 'none') slideDownChatBar();

    addMessage(text, 'user');
    if (userInput) userInput.value = '';
    isProcessing = true;

    const typingIndicator = showTypingIndicator();

    try {
        const response = await sendMessageToBackend(text);
        removeTypingIndicator(typingIndicator);
        addMessage(response, 'ai');
    } catch (error) {
        removeTypingIndicator(typingIndicator);
        addMessage('Sorry, I encountered an error. Please try again.', 'ai');
    } finally {
        isProcessing = false;
    }

    plusPopup?.classList.add('show');
    chatBar?.classList.add('bottomed');
}

// ------------------------
// VOICE INPUT
// ------------------------
async function startVoiceInput() {
    try {
        const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!Recognition) throw new Error('SpeechRecognition not supported');

        const recognition = new Recognition();
        recognition.lang = 'en-US';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => wave && (wave.style.display = 'flex');
        recognition.onend = () => wave && (wave.style.display = 'none');
        recognition.onresult = (event) => {
            if (userInput) userInput.value = event.results[0][0].transcript;
            sendMessage();
        };
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            wave && (wave.style.display = 'none');
            alert('Voice input failed. Please try again or type your message.');
        };

        recognition.start();
    } catch (error) {
        alert('Voice input is not supported in your browser. Please type your message instead.');
    }
}

// ------------------------
// POPUP HANDLING
// ------------------------
function closePlusPopup() {
    plusPopup?.classList.remove('show');
}

function removeUpgradeButton() {
    upgradeBtn?.remove();
}

// ------------------------
// CHAT INITIALIZATION
// ------------------------
async function initChat() {
    try {
        const response = await fetch('/api/chat/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentPersonality = data.defaultPersonality || 'friendly';
    } catch (error) {
        console.error('Chat initialization error:', error);
        currentPersonality = 'friendly';
    }
}

// ------------------------
// ROTATING TITLE TEXT
// ------------------------
function setupRotatingTitle() {
    if (!title) return;
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
}

// ------------------------
// EVENT LISTENERS
// ------------------------
function registerEventListeners() {
    sendBtn?.addEventListener('click', sendMessage);
    userInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    micBtn?.addEventListener('click', startVoiceInput);
    newChatBtn?.addEventListener('click', () => {
        if (chatContainer) chatContainer.innerHTML = '';
        title && (title.style.display = 'block');
        chatBar && (chatBar.style.animation = 'slideToMiddle 0.8s ease forwards');
    });
    closePopup?.addEventListener('click', closePlusPopup);
    closeUpgrade?.addEventListener('click', removeUpgradeButton);
    getStartedBtn?.addEventListener('click', () => {
        const u = localStorage.getItem('aizeeno_user');
        window.location.href = u ? '/templates/chat.html' : '/templates/signup.html';
    });
}

// ------------------------
// INITIALIZATION
// ------------------------
document.addEventListener('DOMContentLoaded', () => {
    initChat();
    setupRotatingTitle();
    registerEventListeners();
    // Initialize subscription flow (if on subscription page)
    if (document.querySelector('.stripe-checkout') || window.location.pathname.includes('/subscription')) {
        initSubscription().catch(err => console.error('Subscription init error:', err));
    }
});

// ------------------------
// SUBSCRIPTION / STRIPE
// ------------------------

async function fetchJson(url, options = {}) {
    // If a relative path is provided, prefix the backend base URL so frontend (port 5500)
    // can access the Flask backend on port 5000.
    if (!/^https?:\/\//i.test(url)) {
        url = BACKEND_BASE + url;
    }
    const res = await fetch(url, options);
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : {}; } catch (e) { data = { raw: text }; }
    if (!res.ok) {
        const err = (data && data.error) ? data.error : `HTTP ${res.status}`;
        throw new Error(err);
    }
    return data;
}

async function fetchWithRetries(path, options = {}, attempts = 4, initialDelay = 400) {
    let lastErr = null;
    const makeUrl = (p) => (/^https?:\/\//i.test(p) ? p : BACKEND_BASE + p);
    for (let i = 0; i < attempts; i++) {
        try {
            const urlToUse = makeUrl(path);
            if (i > 0) console.log(`[subscription] Retry ${i}/${attempts} fetching ${urlToUse}`);
            const data = await fetchJson(urlToUse, options);
            return data;
        } catch (err) {
            lastErr = err;
            const delay = initialDelay * Math.pow(2, i);
            await new Promise(r => setTimeout(r, delay));
        }
    }
    throw lastErr;
}

async function handleReturnFromStripe() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    const plan = urlParams.get('plan');
    if (!sessionId) return;

    const userStr = localStorage.getItem('aizeeno_user');
    if (!userStr) {
        console.warn('[subscription] No local user found; cannot verify payment.');
        return;
    }
    const user = JSON.parse(userStr);

    try {
        const payload = { username: user.username, session_id: sessionId, plan };
        const result = await fetchJson('/api/payment-status', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });

        if (result.success && result.payment) {
            user.subscription = result.subscription || plan || user.subscription || 'starter';
            user.payment = true;
            localStorage.setItem('aizeeno_user', JSON.stringify(user));
            alert(result.message || 'Payment confirmed. Thank you!');
            setTimeout(() => { window.location.href = '/templates/chat.html'; }, 800);
            return;
        }

        if (result.success && !result.payment) {
            alert('Payment not confirmed yet. Please wait a few moments and refresh.');
            return;
        }
        throw new Error(result.error || 'Unknown payment verification response');
    } catch (err) {
        console.error('[subscription] Error verifying payment:', err);
    }
}

async function initSubscription() {
    console.log('[subscription] Initializing subscription flow');
    let config;
    try {
        config = await fetchWithRetries('/api/stripe-config', {}, 5, 300);
    } catch (err) {
        console.error('[subscription] Failed to load Stripe config:', err);
        return;
    }

    const publishableKey = config.publishableKey;
    if (!publishableKey) {
        console.error('[subscription] Missing publishableKey in config');
        return;
    }

    let stripe;
    try {
        stripe = Stripe(publishableKey);
    } catch (err) {
        console.error('[subscription] Stripe initialization failed:', err);
        return;
    }

    const buttons = document.querySelectorAll('.stripe-checkout');
    buttons.forEach((btn) => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const plan = btn.getAttribute('data-plan');
            if (!plan) return;

            const userStr = localStorage.getItem('aizeeno_user');
            if (!userStr) {
                alert('Please log in or sign up before subscribing.');
                window.location.href = '/templates/login.html';
                return;
            }
            const user = JSON.parse(userStr);

            btn.disabled = true;
            const orig = btn.textContent;
            btn.textContent = 'Processing...';

            try {
                const payload = { plan };
                if (user && user.username) payload.username = user.username;
                const resp = await fetchWithRetries('/api/create-checkout-session', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
                }, 3, 300);

                const sessionId = resp.sessionId || resp.id || resp.session_id;
                if (!sessionId) throw new Error('No session id returned from server');

                const { error } = await stripe.redirectToCheckout({ sessionId });
                if (error) throw error;
            } catch (err) {
                console.error('[subscription] Checkout error:', err);
                alert('Unable to start checkout: ' + (err.message || err));
            } finally {
                btn.disabled = false;
                btn.textContent = orig;
            }
        });
    });

    handleReturnFromStripe();
}
