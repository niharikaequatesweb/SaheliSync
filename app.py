from flask import Flask, jsonify
import requests
import json
import config

app = Flask(__name__)

@app.route('/upload-gist', methods=['GET'])
def upload_gist():
    dummy_data = {
        "name": "John Doe",
        "preferences": {
            "cleanliness": 8,
            "pets": "No",
            "sleep_time": "10 PM"
        }
    }

    payload = {
        "description": "Dummy Roommate Profile",
        "public": True,
        "files": {
            "profile.json": {
                "content": json.dumps(dummy_data, indent=2)
            }
        }
    }

    headers = {
        "Authorization": f"token {config.GIST_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post("https://api.github.com/gists", headers=headers, json=payload)

    if response.status_code == 201:
        gist_url = response.json().get("html_url")
        return jsonify({"status": "success", "url": gist_url})
    else:
        return jsonify({
            "status": "error",
            "code": response.status_code,
            "response": response.json()
        }), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
