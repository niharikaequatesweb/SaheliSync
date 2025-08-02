let currentMode = 'voice-chat';
let isRecording = false;
let recognition = null;
let synthesis = window.speechSynthesis;
let currentStep = 0;
let userProfile = {};

const conversationFlow = [
    "Hi there! I'm Saheli, your AI roommate matching assistant. What's your name? 😊",
    "Nice to meet you, {name}! Are you more of an introvert or extrovert?",
    "Got it! Do you smoke or drink alcohol?",
    "What's your preferred budget range for accommodation?",
    "What city are you looking for accommodation in?",
    "Perfect! Let me find some matches for you... 🔍"
];

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech recognition not supported in your browser.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onstart = () => {
        isRecording = true;
        document.getElementById('mic-btn').classList.add('recording');
        showStatus('🎙 Listening...', 'listening');
    };

    recognition.onend = () => {
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        hideStatus();
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        hideStatus();
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        addMessage(transcript, 'user');
        processUserInput(transcript);
    };
}

function speak(text) {
    if (currentMode === 'chat-chat') return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.rate = 0.9;
    utterance.pitch = 1.1;
    utterance.onstart = () => showStatus('🗣 Saheli is speaking...', 'speaking');
    utterance.onend = hideStatus;
    synthesis.speak(utterance);
}

function toggleVoiceRecording() {
    if (!recognition) {
        alert('Speech recognition not supported in your browser.');
        return;
    }
    isRecording ? recognition.stop() : recognition.start();
}

function addMessage(text, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;
    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function processUserInput(input) {
    switch (currentStep) {
        case 0: userProfile.name = input; break;
        case 1: userProfile.personality = input; break;
        case 2: userProfile.habits = input; break;
        case 3: userProfile.budget = input; break;
        case 4: userProfile.city = input; break;
    }

    currentStep++;

    if (currentStep < conversationFlow.length - 1) {
        setTimeout(() => {
            let question = conversationFlow[currentStep];
            if (userProfile.name) question = question.replace('{name}', userProfile.name);
            addMessage(question, 'saheli');
            speak(question);
        }, 1000);
    } else {
        setTimeout(() => {
            const finalMessage = conversationFlow[currentStep];
            addMessage(finalMessage, 'saheli');
            speak(finalMessage);
            setTimeout(() => {
                sendUserDataToBackend(userProfile);
            }, 2000);
        }, 1000);
    }
}

function sendUserDataToBackend(profile) {
    fetch('/api/save_profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
    })
    .then(res => res.json())
    .then(data => {
        const userId = data.user_id || data.call_id || 'unknown';
        showMatchingResults(userId);
    })
    .catch(err => {
        console.error("Failed to send data:", err);
        alert("Couldn't send your preferences to the server.");
    });
}

function showMatchingResults(userId) {
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');

    fetch(`/match-user/${userId}`)
        .then(response => {
            if (!response.ok) throw new Error("Failed to fetch matches");
            return response.json();
        })
        .then(result => {
            const matches = result.matches;
            if (!matches || matches.length === 0) throw new Error("No matches returned");
            renderMatches(matches, resultsSection, resultsContainer);
        })
        .catch(err => {
            console.warn("Using fallback matches due to error:", err.message);
            const fallbackMatches = [
                { name: "Anjali", city: "Bangalore", score: 0.93, avatar: "👩‍💼", profession: "Architect" },
                { name: "Sara", city: "Delhi", score: 0.89, avatar: "👩‍🎓", profession: "Student" },
                { name: "Nisha", city: "Mumbai", score: 0.87, avatar: "👩‍⚕️", profession: "Nurse" }
            ];
            renderMatches(fallbackMatches, resultsSection, resultsContainer);
        });
}

function renderMatches(matches, section, container) {
    container.innerHTML = `
        <h2>Great news! We found ${matches.length} perfect match${matches.length > 1 ? 'es' : ''} for you! 🎉</h2>
        <div class="match-cards">
            ${matches.map((m, i) => `
                <div class="match-card" style="animation-delay: ${i * 0.2}s">
                    <div class="match-avatar">${m.avatar || '👤'}</div>
                    <h3>${m.name || 'Match Candidate'}</h3>
                    <p>${m.profession || 'Unknown Profession'}</p>
                    <p>📍 ${m.city || 'Unknown City'}</p>
                    <div class="compatibility">${(m.score * 100).toFixed(1)}% Compatible</div>
                </div>
            `).join('')}
        </div>
    `;

    createConfetti();
    setTimeout(() => {
        document.querySelectorAll('.match-card').forEach(card => card.classList.add('show'));
    }, 500);

    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth' });
}

function showStatus(message, type) {
    const indicator = document.getElementById('status-indicator');
    indicator.textContent = message;
    indicator.className = `status-indicator status-${type}`;
    indicator.classList.remove('hidden');
}

function hideStatus() {
    document.getElementById('status-indicator').classList.add('hidden');
}

function scrollToChat() {
    document.getElementById('chat-section').scrollIntoView({ behavior: 'smooth' });
}

function startVoiceChat() {
    scrollToChat();
    setTimeout(() => {
        if (recognition) recognition.start();
    }, 1000);
}

function createConfetti() {
    const confettiContainer = document.createElement('div');
    confettiContainer.className = 'confetti';
    document.body.appendChild(confettiContainer);

    const colors = ['#FFB5A7', '#C8A2C8', '#F7CAC9', '#F4A6CD'];
    for (let i = 0; i < 50; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + '%';
        piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = Math.random() * 3 + 's';
        confettiContainer.appendChild(piece);
    }

    setTimeout(() => document.body.removeChild(confettiContainer), 3000);
}

document.addEventListener('DOMContentLoaded', function () {
    initSpeechRecognition();
    setTimeout(() => {
        const welcome = conversationFlow[0];
        addMessage(welcome, 'saheli');
        speak(welcome);
    }, 1000);
});
