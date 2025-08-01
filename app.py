from omnidimension import Client
import json
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

api_key = 'ASyEXtdTuHuc5bhGLlwEmteCM3xQ5xnkavicb5_bCao'
client = Client(api_key)

def create_roommate_agent():
    try:
        response = client.agent.create(
            name="Roommate Match AI Voice Collector",
            welcome_message="Hi! I'm here to collect your roommate preferences through voice. Are you ready to begin?",
            context_breakdown=[
                {"title": "Introduction", "body": "I'll ask you about your lifestyle preferences.", "is_enabled": True},
                {"title": "Cleanliness", "body": "How important is cleanliness to you?", "is_enabled": True},
                {"title": "Sleep", "body": "What time do you go to bed and wake up?", "is_enabled": True},
                {"title": "Social Life", "body": "Do you like having friends over?", "is_enabled": True},
                {"title": "Privacy", "body": "Do you prefer a private room?", "is_enabled": True},
                {"title": "Other", "body": "Pets? Smoking? Dietary restrictions?", "is_enabled": True},
                {"title": "Summary", "body": "Summarize preferences and ask for confirmation.", "is_enabled": True},
            ],
            call_type="Outgoing",
            transcriber={
                "provider": "deepgram_stream",
                "silence_timeout_ms": 2000,
                "model": "nova-3",
                "numerals": True,
                "punctuate": True,
                "smart_format": True,
                "diarize": False
            },
            model={"model": "gpt-4o-mini", "temperature": 0.3},
            voice={"provider": "eleven_labs", "voice_id": "cgSgspJ2msm6clMCkdW9"},
            post_call_actions={
                "webhook": {
                    "enabled": True,
                    "url": "https://sahelisync.onrender.com/omnidim-callback",
                    "include": ["summary", "fullConversation", "sentiment", "extracted_variables"],
                    "extracted_variables": [
                        {"key": "cleanliness_rating", "prompt": "Extract the cleanliness rating (1-10)."},
                        {"key": "cleanliness_habits", "prompt": "Describe cleaning habits."},
                        {"key": "bedtime", "prompt": "Extract bedtime."},
                        {"key": "wake_time", "prompt": "Extract wake time."},
                        {"key": "sleep_type", "prompt": "Light or heavy sleeper?"},
                        {"key": "social_energy", "prompt": "Social energy rating (1-10)."},
                        {"key": "guests_preference", "prompt": "Frequency of guests."},
                        {"key": "room_preference", "prompt": "Private/shared room?"},
                        {"key": "privacy_importance", "prompt": "Importance of personal space."},
                        {"key": "pets", "prompt": "Pets info."},
                        {"key": "substances", "prompt": "Smoking/drinking info."},
                        {"key": "dietary", "prompt": "Dietary restrictions."},
                        {"key": "noise_tolerance", "prompt": "Music/noise preferences."}
                    ]
                }
            }
        )
        return response.get("id")
    except Exception as e:
        print(f"Agent creation failed: {e}")
        return None

def initiate_call(agent_id, phone_number):
    try:
        result = client.call.create(
            agent_id=agent_id,
            phone_number=phone_number,
            call_type="Outgoing"
        )
        return result
    except Exception as e:
        print(f"Call initiation failed: {e}")
        return None

def process_voice_to_json(data):
    ex = data.get("extracted_variables", {})
    return {
        "user_profile": {
            "cleanliness": {"rating": ex.get("cleanliness_rating"), "habits": ex.get("cleanliness_habits")},
            "sleep_schedule": {"bedtime": ex.get("bedtime"), "wake_time": ex.get("wake_time"), "sleep_type": ex.get("sleep_type")},
            "social": {"energy": ex.get("social_energy"), "guests": ex.get("guests_preference")},
            "living": {"room_type": ex.get("room_preference"), "privacy": ex.get("privacy_importance")},
            "lifestyle": {"pets": ex.get("pets"), "substances": ex.get("substances"), "dietary": ex.get("dietary"), "noise": ex.get("noise_tolerance")}
        },
        "summary": data.get("summary"),
        "sentiment": data.get("sentiment"),
        "full_conversation": data.get("fullConversation"),
        "timestamp": datetime.now().isoformat()
    }

@app.route('/')
def root():
    return jsonify({"status": "SaheliSync is running"})

@app.route('/create-agent', methods=['POST'])
def create_agent():
    agent_id = create_roommate_agent()
    if agent_id:
        return jsonify({"status": "success", "agent_id": agent_id})
    else:
        return jsonify({"status": "error", "message": "Failed to create agent"}), 500

@app.route('/initiate-call', methods=['POST'])
def call_user():
    data = request.json
    agent_id = data.get("agent_id")
    phone = data.get("phone_number")
    result = initiate_call(agent_id, phone)
    if result:
        return jsonify({"status": "success", "details": result})
    else:
        return jsonify({"status": "error", "message": "Call initiation failed"}), 500

@app.route('/omnidim-callback', methods=['POST'])
def webhook():
    data = request.json
    prefs = process_voice_to_json(data)
    filename = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(prefs, f, indent=2)
    return jsonify({"status": "received", "filename": filename})

if __name__ == '__main__':
    app.run(debug=True, port=5000)