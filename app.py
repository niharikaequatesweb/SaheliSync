from flask import Flask, request, jsonify, render_template
from omnidimension import Client
from datetime import datetime
import json
import os
import traceback
import requests
import config
from flask_cors import CORS

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

client = Client(config.OMNIDIM_API_KEY)

# Global variable to store the latest callback data
latest_profile_data = None
all_profiles = []  # Store multiple profiles if needed


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
        traceback.print_exc()
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
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/omnidim-callback', methods=['POST'])
def omnidim_callback():
    global latest_profile_data, all_profiles
    
    try:
        data = request.get_json(force=True)
        print("[Callback received]", json.dumps(data, indent=2))

        call_report = data.get("call_report", {})
        
        # Store in global variables instead of files
        latest_profile_data = call_report
        
        # Add timestamp for tracking
        call_report['timestamp'] = datetime.now().isoformat()
        all_profiles.append(call_report)
        
        print(f"[Stored callback data in memory] Total profiles: {len(all_profiles)}")

        # Still upload to paste.gg for backup/sharing
        paste_url = upload_to_pastegg(call_report)

        # Process the data immediately
        processed_data = process_profile_data(call_report)

        return jsonify({
            "status": "received",
            "stored_in_memory": True,
            "paste_url": paste_url,
            "processed_data": processed_data
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


def process_profile_data(call_report):
    """Process the profile data and extract useful information"""
    try:
        extracted_vars = call_report.get("extracted_variables", {})
        summary = call_report.get("summary", "")
        
        # Create a structured profile
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
        print(f"[Error processing profile data]: {e}")
        return None


def upload_to_pastegg(data):
    try:
        paste_data = {
            "name": "sahelisync-callback.json",
            "files": [
                {
                    "name": "roommate_preferences.json",
                    "content": {
                        "format": "text",
                        "value": json.dumps(data, indent=2)
                    }
                }
            ],
            "visibility": "public"
        }

        response = requests.post("https://api.paste.gg/v1/pastes", json=paste_data)

        if response.status_code == 201:
            paste_id = response.json()["result"]["id"]
            paste_url = f"https://paste.gg/p/{paste_id}"
            print(f"[Uploaded to Paste.gg]: {paste_url}")
            return paste_url
        else:
            print(f"[Paste.gg upload failed]: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[Paste.gg upload error]: {e}")
        return None


@app.route('/latest-profile', methods=['GET'])
def get_latest_profile():
    if latest_profile_data:
        return jsonify(latest_profile_data)
    else:
        return jsonify({"error": "No profile data found"}), 404


@app.route('/all-profiles', methods=['GET'])
def get_all_profiles():
    """Get all stored profiles"""
    return jsonify({
        "total": len(all_profiles),
        "profiles": all_profiles
    })


@app.route('/processed-profile', methods=['GET'])
def get_processed_profile():
    """Get the latest processed profile data"""
    if latest_profile_data:
        processed = process_profile_data(latest_profile_data)
        return jsonify(processed)
    else:
        return jsonify({"error": "No profile data found"}), 404


@app.route('/clear-profiles', methods=['POST'])
def clear_profiles():
    """Clear all stored profile data"""
    global latest_profile_data, all_profiles
    latest_profile_data = None
    all_profiles = []
    return jsonify({"status": "cleared", "message": "All profile data cleared from memory"})


@app.route('/profile-stats', methods=['GET'])
def get_profile_stats():
    """Get statistics about stored profiles"""
    if not all_profiles:
        return jsonify({"error": "No profiles found"}), 404
    
    stats = {
        "total_profiles": len(all_profiles),
        "latest_timestamp": all_profiles[-1].get("timestamp") if all_profiles else None,
        "oldest_timestamp": all_profiles[0].get("timestamp") if all_profiles else None,
        "available_data_points": []
    }
    
    # Analyze what data points are available
    if latest_profile_data:
        extracted_vars = latest_profile_data.get("extracted_variables", {})
        stats["available_data_points"] = list(extracted_vars.keys())
        print(extracted_vars)
    
    return jsonify(stats)


@app.route('/download-paste', methods=['GET'])
def download_paste():
    paste_url = request.args.get("url")
    if not paste_url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    try:
        paste_id = paste_url.rstrip("/").split("/")[-1]
        api_url = f"https://api.paste.gg/v1/pastes/{paste_id}"
        response = requests.get(api_url)

        if response.status_code != 200:
            return jsonify({"error": f"Failed to fetch paste.gg content: {response.status_code}"}), 500

        file_content = response.json()["result"]["files"][0]["content"]["value"]
        
        # Store in memory instead of file
        global latest_profile_data
        latest_profile_data = json.loads(file_content)
        
        return jsonify({
            "status": "success", 
            "message": "Data loaded into memory",
            "data": latest_profile_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)