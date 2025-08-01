from flask import Flask, request, jsonify, render_template
from omnidimension import Client
from datetime import datetime
import json
import os
import config  # Your new config file

app = Flask(__name__, static_folder="static", template_folder="templates")

# Omnidimension client setup using value from config
client = Client(config.OMNIDIM_API_KEY)

@app.context_processor
def inject_widget_config():
    return dict(
        voice_widget_script_id=config.VOICE_WIDGET_SCRIPT_ID,
        voice_widget_script_src=f"{config.VOICE_WIDGET_SCRIPT_BASE}?secret_key={config.VOICE_WIDGET_SECRET}"
    )

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/create-agent', methods=['POST'])
def create_agent():
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
        return jsonify({"status": "success", "agent_id": response.get("id")})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/initiate-call', methods=['POST'])
def initiate_call():
    try:
        data = request.json
        agent_id = data.get("agent_id")
        phone = data.get("phone_number")
        result = client.call.create(agent_id=agent_id, phone_number=phone, call_type="Outgoing")
        return jsonify({"status": "success", "details": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/omnidim-callback', methods=['POST'])
def omnidim_callback():
    try:
        data = request.get_json(force=True)
        ex = data.get("extracted_variables", {})

        processed = {
            "user_profile": {
                "cleanliness": {
                    "rating": ex.get("cleanliness_rating"),
                    "habits": ex.get("cleanliness_habits")
                },
                "sleep_schedule": {
                    "bedtime": ex.get("bedtime"),
                    "wake_time": ex.get("wake_time"),
                    "sleep_type": ex.get("sleep_type")
                },
                "social": {
                    "energy": ex.get("social_energy"),
                    "guests": ex.get("guests_preference")
                },
                "living": {
                    "room_type": ex.get("room_preference"),
                    "privacy": ex.get("privacy_importance")
                },
                "lifestyle": {
                    "pets": ex.get("pets"),
                    "substances": ex.get("substances"),
                    "dietary": ex.get("dietary"),
                    "noise": ex.get("noise_tolerance")
                }
            },
            "summary": data.get("summary"),
            "sentiment": data.get("sentiment"),
            "full_conversation": data.get("fullConversation"),
            "timestamp": datetime.now().isoformat()
        }

        # Save JSON to file
        os.makedirs("data", exist_ok=True)
        filename = f"data/user_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(processed, f, indent=2)

        return jsonify({"status": "received", "filename": filename})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
