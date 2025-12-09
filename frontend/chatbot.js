const API_CHAT_URL = "http://127.0.0.1:8000/api/chat";

// ---------------------------
// UI References
// ---------------------------
const getUI = () => ({
    chatWindow: document.getElementById('chatWindow'),
    userInput: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    logoutBtn: document.querySelector('.logout-btn')
});

// ---------------------------
// INITIALIZATION
// ---------------------------
document.addEventListener('DOMContentLoaded', () => {
    const { userInput, sendBtn, logoutBtn } = getUI();

    if (userInput) userInput.focus();

    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    if (userInput) userInput.addEventListener('keydown', (e) => e.key === 'Enter' && sendMessage());

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('stockUser');
            window.location.href = 'login.html';
        });
    }
});

// ---------------------------
// QUICK COMMAND BUTTONS
// ---------------------------
document.addEventListener('click', (e) => {
    const button = e.target.closest('button[data-query]');
    if (!button) return;

    const query = button.getAttribute('data-query');
    const { userInput } = getUI();
    if (userInput && query) {
        userInput.value = query;
        userInput.focus();
    }
});

// ---------------------------
// CHAT LOGIC
// ---------------------------
async function sendMessage() {
    const { userInput, chatWindow } = getUI();
    if (!userInput || !chatWindow) return;

    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, 'user');
    userInput.value = '';

    const typingId = showTypingIndicator();
    scrollToBottom();

    try {
        const response = await fetch(API_CHAT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        removeTypingIndicator(typingId);

        if (response.ok) {
            addMessage(data.response, 'bot');
        } else {
            console.error("API Error:", data);
            addMessage("Error: Could not reach server.", 'bot');
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        console.error("Network Error:", error);
        addMessage("Network error. Check console.", 'bot');
    }

    scrollToBottom();
}

// ---------------------------
// MESSAGE HANDLERS
// ---------------------------
function addMessage(text, sender) {
    const { chatWindow } = getUI();
    if (!chatWindow) return;

    const div = document.createElement('div');
    div.className = `message ${sender}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    div.innerHTML = `
        <div class="bubble">${text}</div>
        <div class="timestamp">${time}</div>
    `;
    chatWindow.appendChild(div);
}

function showTypingIndicator() {
    const { chatWindow } = getUI();
    if (!chatWindow) return null;

    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'message bot';
    div.innerHTML = `<div class="bubble" style="color:#888; font-style:italic;">AI is typing...</div>`;
    chatWindow.appendChild(div);

    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    const { chatWindow } = getUI();
    if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
}