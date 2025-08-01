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

// Initialize speech recognition
function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn("Speech recognition not supported.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onstart = () => {
        isRecording = true;
        document.getElementById('mic-btn').classList.add('recording');
        showStatus('Listening...', 'listening');
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        addMessage(transcript, 'user');
        processUserInput(transcript);
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        hideStatus();
    };

    recognition.onend = () => {
        isRecording = false;
        document.getElementById('mic-btn').classList.remove('recording');
        hideStatus();
    };
}

// Text-to-speech
function speak(text) {
    if (currentMode === 'chat-chat') return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.rate = 0.9;
    utterance.pitch = 1.1;

    utterance.onstart = () => showStatus('Saheli is speaking...', 'speaking');
    utterance.onend = hideStatus;

    synthesis.speak(utterance);
}

function setMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(mode + '-btn').classList.add('active');
}

function toggleVoiceRecording() {
    if (!recognition) {
        alert('Speech recognition not supported in your browser');
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
            setTimeout(showMatchingResults, 3000);
        }, 1000);
    }
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (message) {
        addMessage(message, 'user');
        processUserInput(message);
        input.value = '';
    }
}

function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
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

function showMatchingResults() {
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');
    const hasMatches = Math.random() > 0.3;

    if (hasMatches) {
        const matches = [
            { name: 'Priya Sharma', profession: 'Software Engineer', compatibility: '95%', city: 'Bangalore', avatar: '👩‍💻' },
            { name: 'Ananya Gupta', profession: 'Marketing Manager', compatibility: '88%', city: 'Mumbai', avatar: '👩‍💼' },
            { name: 'Kavya Reddy', profession: 'Graphic Designer', compatibility: '82%', city: 'Hyderabad', avatar: '👩‍🎨' }
        ];

        resultsContainer.innerHTML = `
            <h2>Great news! We found ${matches.length} perfect matches for you! 🎉</h2>
            <div class="match-cards">
                ${matches.map((m, i) => `
                    <div class="match-card" style="animation-delay: ${i * 0.2}s">
                        <div class="match-avatar">${m.avatar}</div>
                        <h3>${m.name}</h3>
                        <p>${m.profession}</p>
                        <p>📍 ${m.city}</p>
                        <div class="compatibility">${m.compatibility} Compatible</div>
                    </div>`).join('')}
            </div>
        `;

        createConfetti();

        setTimeout(() => {
            document.querySelectorAll('.match-card').forEach(card => card.classList.add('show'));
        }, 500);
    } else {
        resultsContainer.innerHTML = `
            <div class="no-match">
                <h2>We're still looking for your perfect match! 🔍</h2>
                <p>We'll notify you when we find someone compatible with your preferences.</p>
                <div class="phone-input">
                    <input type="tel" placeholder="Enter your phone number" id="phone-number">
                    <button class="btn btn-primary" onclick="submitPhoneNumber()">Notify Me</button>
                </div>
            </div>
        `;
    }

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth' });
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

function submitPhoneNumber() {
    const number = document.getElementById('phone-number').value;
    if (number) {
        alert("Thank you! We'll notify you when we find a match.");
        console.log('Phone submitted:', number);

        // Example fetch to Flask endpoint:
        // fetch('/submit-phone', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify({ phone: number })
        // });
    }
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

document.addEventListener('DOMContentLoaded', function () {
    initSpeechRecognition();
    setTimeout(() => speak(conversationFlow[0]), 1000);
});
