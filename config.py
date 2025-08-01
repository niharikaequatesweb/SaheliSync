# config.py

import os

OMNIDIM_API_KEY = os.getenv("OMNIDIM_API_KEY", "ASyEXtdTuHuc5bhGLlwEmteCM3xQ5xnkavicb5_bCao")
VOICE_WIDGET_SECRET = os.getenv("VOICE_WIDGET_SECRET", "99a0f197aa77b8aad9ca8f9a237efe4e")

# For the <script> tag
VOICE_WIDGET_SCRIPT_ID = "omnidimension-web-widget"
VOICE_WIDGET_SCRIPT_BASE = "https://backend.omnidim.io/web_widget.js"