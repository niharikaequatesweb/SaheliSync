import logging
from flask import Flask, request, jsonify, render_template
from omnidimension import Client
from datetime import datetime
import os
import traceback
from flask_cors import CORS
from model import RoommateMatchingModel
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

client = Client(config.OMNIDIM_API_KEY)

latest_profile_data = None
all_profiles = []

@app.context_processor
def inject_widget_config():
    return dict(
        voice_widget_script_id=config.VOICE_WIDGET_SCRIPT_ID,
        voice_widget_script_src=f"{config.VOICE_WIDGET_SCRIPT_BASE}?secret_key={config.VOICE_WIDGET_SECRET}"
    )

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "SaheliSync is running."})

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
        logger.exception("Failed to create agent")
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
        logger.exception("Failed to initiate call")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/omnidim-callback', methods=['POST'])
def omnidim_callback():
    global latest_profile_data, all_profiles
    try:
        data = request.get_json(force=True)
        call_report = data.get("call_report", {})
        call_report['timestamp'] = datetime.now().isoformat()

        latest_profile_data = call_report
        all_profiles.append(call_report)

        logger.info(f"✅ Callback received. Total profiles stored: {len(all_profiles)}")
        processed_data = process_profile_data(call_report)

        return jsonify({
            "status": "received",
            "stored_in_memory": True,
            "total_profiles": len(all_profiles),
            "processed_data": processed_data
        })
    except Exception as e:
        logger.exception("Error in /omnidim-callback")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_profile_data(call_report):
    try:
        extracted_vars = call_report.get("extracted_variables", {})
        summary = call_report.get("summary", "")
        profile = {
            "user_id": call_report.get("call_id", "unknown"),
            "preferences": {
                "cleanliness": {
                    "rating": extracted_vars.get("cleanliness_rating"),
                    "habits": extracted_vars.get("cleanliness_habits")
                },
                "sleep": {
                    "bedtime": extracted_vars.get("bedtime"),
                    "wake_time": extracted_vars.get("wake_time"),
                    "sleep_type": extracted_vars.get("sleep_type")
                },
                "social": {
                    "energy_rating": extracted_vars.get("social_energy"),
                    "guests_preference": extracted_vars.get("guests_preference")
                },
                "living": {
                    "room_preference": extracted_vars.get("room_preference"),
                    "privacy_importance": extracted_vars.get("privacy_importance")
                },
                "lifestyle": {
                    "pets": extracted_vars.get("pets"),
                    "substances": extracted_vars.get("substances"),
                    "dietary": extracted_vars.get("dietary"),
                    "noise_tolerance": extracted_vars.get("noise_tolerance")
                }
            },
            "summary": summary,
            "sentiment": call_report.get("sentiment"),
            "timestamp": call_report.get("timestamp")
        }
        return profile
    except Exception as e:
        logger.error(f"[Error processing profile data]: {e}")
        return None

@app.route('/match-user/<user_id>', methods=['GET'])
def match_user(user_id):
    if not all_profiles or len(all_profiles) < 2:
        return jsonify({"error": "Need at least 2 profiles to perform matching"}), 400

    matcher = RoommateMatchingModel()
    result = matcher.find_matches(all_profiles, user_id)

    if "error" in result:
        return jsonify(result), 404

    logger.info(f"\n📊 Match Results for User ID {user_id}:")
    for match in result.get("matches", []):
        logger.info(f" - Matched User ID: {match['user_id']} | Score: {match['score']:.2f}")

    return jsonify(result)

@app.route('/test-matching', methods=['GET'])
def test_matching():
    if len(all_profiles) < 2:
        return jsonify({"error": "At least 2 profiles are required to test matching."}), 400

    target_id = all_profiles[-1].get("call_id")
    matcher = RoommateMatchingModel()
    result = matcher.find_matches(all_profiles, target_id)

    logger.info(f"\n🧪 Test Match for User ID {target_id}:")
    for match in result.get("matches", []):
        logger.info(f" - Matched User ID: {match['user_id']} | Score: {match['score']:.2f}")

    return jsonify(result)

@app.route('/data-summary', methods=['GET'])
def get_data_summary():
    return jsonify({
        "memory_status": "active",
        "latest_profile_available": latest_profile_data is not None,
        "total_profiles_stored": len(all_profiles),
        "last_update": all_profiles[-1].get("timestamp") if all_profiles else None,
        "available_endpoints": [
            "/latest-profile",
            "/all-profiles", 
            "/processed-profile",
            "/analyze-profiles",
            "/profile-stats",
            "/clear-profiles",
            "/data-summary",
            "/match-user/<user_id>",
            "/test-matching"
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
