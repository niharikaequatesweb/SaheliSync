# config.py

import os

OMNIDIM_API_KEY = os.getenv("OMNIDIM_API_KEY", "jVRwY6AyEWquGevctQe-OdxKBaxcD8uLtAUP1cfjd1o")
VOICE_WIDGET_SECRET = os.getenv("VOICE_WIDGET_SECRET", "d71809ab901a0e64cf4529da1b8c3628")

# For the <script> tag
VOICE_WIDGET_SCRIPT_ID = "omnidimension-web-widget"
VOICE_WIDGET_SCRIPT_BASE = "https://backend.omnidim.io/web_widget.js"