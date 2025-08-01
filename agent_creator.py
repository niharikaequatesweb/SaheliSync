from omnidimension import Client
import json
from flask import Flask, request, jsonify


api_key='ASyEXtdTuHuc5bhGLlwEmteCM3xQ5xnkavicb5_bCao'
client = Client(api_key)


def create_roommate_agent():
    try:
        response = client.agent.create(
            name="Roommate Match AI Voice Collector",
            welcome_message="Hi! I'm here to collect your roommate preferences through voice. I'll ask you a few questions and then provide your preferences in a structured format. Are you ready to begin?",

            context_breakdown=[
                {
                    "title": "Introduction and Data Collection Purpose",
                    "body": "Explain that you'll collect their preferences through voice and convert them to structured data. Ask: 'I'll ask you about your lifestyle preferences and organize them for you. Ready to start?'",
                    "is_enabled": True
                },
                {
                    "title": "Cleanliness Preferences Collection",
                    "body": "Ask: 'On a scale of 1-10, how important is cleanliness to you? 1 being very relaxed about mess, 10 being extremely tidy. Also, tell me about your cleaning habits.'",
                    "is_enabled": True
                },
                {
                    "title": "Sleep Schedule and Habits",
                    "body": "Ask: 'What time do you usually go to bed and wake up? Are you a light or heavy sleeper? Do you prefer quiet environments?'",
                    "is_enabled": True
                },
                {
                    "title": "Social Preferences and Lifestyle",
                    "body": "Ask: 'Do you enjoy having friends over often? Do you prefer quiet evenings or social gatherings? How would you rate your social energy level from 1-10?'",
                    "is_enabled": True
                },
                {
                    "title": "Living Space and Privacy Needs",
                    "body": "Ask: 'Do you prefer having your own private room or are you comfortable sharing? How important is personal space to you?'",
                    "is_enabled": True
                },
                {
                    "title": "Additional Preferences",
                    "body": "Ask: 'Do you have any pets? Do you smoke or drink? Any dietary restrictions? Music/noise preferences?'",
                    "is_enabled": True
                },
                {
                    "title": "Data Summary and Confirmation",
                    "body": "Summarize all collected information and ask for confirmation before ending the call.",
                    "is_enabled": True
                }
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

            model={
                "model": "gpt-4o-mini",
                "temperature": 0.3
            },

            voice={
                "provider": "eleven_labs",
                "voice_id": "cgSgspJ2msm6clMCkdW9"
            },

            post_call_actions={
                "webhook": {
                    "enabled": True,
                    "url": "https://your-ngrok-url.ngrok.io/omnidim-callback",  # Update this with your ngrok URL
                    "include": ["summary", "fullConversation", "sentiment", "extracted_variables"],
                    "extracted_variables": [
                        {"key": "cleanliness_rating", "prompt": "Extract the cleanliness rating (1-10) from user's response."},
                        {"key": "cleanliness_habits", "prompt": "Extract user's cleaning habits description."},
                        {"key": "bedtime", "prompt": "Extract bedtime in 24-hour format."},
                        {"key": "wake_time", "prompt": "Extract wake time in 24-hour format."},
                        {"key": "sleep_type", "prompt": "Extract if user is light or heavy sleeper."},
                        {"key": "social_energy", "prompt": "Extract social energy rating (1-10)."},
                        {"key": "guests_preference", "prompt": "Extract frequency of having guests over."},
                        {"key": "room_preference", "prompt": "Extract private vs shared room preference."},
                        {"key": "privacy_importance", "prompt": "Extract importance of personal space."},
                        {"key": "pets", "prompt": "Extract pet ownership and preferences."},
                        {"key": "substances", "prompt": "Extract smoking/drinking habits."},
                        {"key": "dietary", "prompt": "Extract dietary restrictions."},
                        {"key": "noise_tolerance", "prompt": "Extract music/noise preferences."}
                    ]
                }
            }
        )

        print("Agent created successfully!")
        print(f"Full response: {response}")

        # Try to extract agent ID from different possible response formats
        agent_id = None
        if isinstance(response, dict):
            agent_id = response.get('id') or response.get('agent_id') or response.get('data', {}).get('id')

        if agent_id:
            print(f"Agent ID: {agent_id}")
            return agent_id
        else:
            print("Agent ID not found in response. Check the response structure above.")
            return None

    except Exception as e:
        print(f"Error creating agent: {e}")
        return None

# Step 2: Webhook Server (webhook_server.py)
from flask import Flask, request, jsonify
import json
from datetime import datetime

app = Flask(__name__)

def process_voice_to_json(webhook_data):
    """Convert webhook data to structured JSON"""
    extracted_vars = webhook_data.get('extracted_variables', {})

    user_preferences = {
        "user_profile": {
            "cleanliness": {
                "rating": extracted_vars.get('cleanliness_rating', 'Not specified'),
                "habits": extracted_vars.get('cleanliness_habits', 'Not specified')
            },
            "sleep_schedule": {
                "bedtime": extracted_vars.get('bedtime', 'Not specified'),
                "wake_time": extracted_vars.get('wake_time', 'Not specified'),
                "sleep_type": extracted_vars.get('sleep_type', 'Not specified')
            },
            "social_preferences": {
                "energy_level": extracted_vars.get('social_energy', 'Not specified'),
                "guests_frequency": extracted_vars.get('guests_preference', 'Not specified')
            },
            "living_preferences": {
                "room_type": extracted_vars.get('room_preference', 'Not specified'),
                "privacy_importance": extracted_vars.get('privacy_importance', 'Not specified')
            },
            "lifestyle": {
                "pets": extracted_vars.get('pets', 'Not specified'),
                "substances": extracted_vars.get('substances', 'Not specified'),
                "dietary": extracted_vars.get('dietary', 'Not specified'),
                "noise_tolerance": extracted_vars.get('noise_tolerance', 'Not specified')
            }
        },
        "conversation_metadata": {
            "sentiment": webhook_data.get('sentiment', 'Not analyzed'),
            "summary": webhook_data.get('summary', 'Not available'),
            "full_conversation": webhook_data.get('fullConversation', 'Not available'),
            "processed_at": datetime.now().isoformat()
        }
    }

    return user_preferences

@app.route('/omnidim-callback', methods=['POST'])
def handle_omnidim_callback():
    try:
        print("Received webhook callback!")
        webhook_data = request.json
        print(f"Webhook data: {json.dumps(webhook_data, indent=2)}")

        # Process voice input to JSON
        preferences_json = process_voice_to_json(webhook_data)

        # Save to file
        filename = f"user_preferences_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(preferences_json, f, indent=2)

        print(f"Preferences saved to {filename}")
        print("Structured preferences:")
        print(json.dumps(preferences_json, indent=2))

        return jsonify({"status": "success", "message": "Preferences processed", "filename": filename})

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("Starting webhook server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)

# Step 3: Call Initiator (make_call.py)
def initiate_call(agent_id, phone_number):
    """Initiate a call with the created agent"""
    try:
        call_response = client.call.create(
            agent_id=agent_id,
            phone_number=phone_number,  # Format: "+1234567890"
            call_type="Outgoing"
        )

        print(f"Call initiated successfully!")
        print(f"Call response: {call_response}")
        return call_response

    except Exception as e:
        print(f"Error initiating call: {e}")
        return None

@app.route('/')
def home():
    return "Flask app is running! Welcome to SaheliSync"

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "message": "Server is running"})

@app.route('/routes')
def list_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

# Step 4: Main execution function
def main():
    print("=== Roommate Preferences Voice Collection System ===\n")

    # Create agent
    print("1. Creating agent...")
    agent_id = create_roommate_agent()

    if not agent_id:
        print("Failed to create agent. Please check your API key and try again.")
        return

    print(f"\n2. Agent created with ID: {agent_id}")
    print("\n3. Next steps:")
    print("   a. Start the webhook server (run webhook_server.py)")
    print("   b. Use ngrok to expose your local server: 'ngrok http 5000'")
    print("   c. Update the webhook URL in the agent creation code")
    print("   d. Initiate a call using the agent ID")
    print(f"\n4. To make a call, use:")
    print(f"   initiate_call('{agent_id}', '+1234567890')")

if __name__ == "__main__":
    main()