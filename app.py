import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from eligible_texts import get_eligible_texts

os.environ["FLASK_RUN_HOST"] = "0.0.0.0"
os.environ["FLASK_RUN_PORT"] = os.environ.get("PORT", "5000")

app = Flask(__name__, static_folder="static")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Load cdn_map.json once at startup
try:
    with open("cdn_map.json", "r", encoding="utf-8") as f:
        cdn_map = json.load(f)
    print(f"🗺️ Loaded cdn_map.json with {len(cdn_map)} entries", flush=True)
except Exception as e:
    cdn_map = {}
    print(f"⚠️ Failed to load cdn_map.json: {e}", flush=True)

@app.route("/")
def index():
    return "Mural API is running", 200

@app.route("/health")
def health():
    return "OK", 200

@app.route("/api/murals", methods=["POST"])
def get_murals():
    try:
        data = request.get_json()
        wall_width = float(data.get("wall_width", 0))
        wall_height = float(data.get("wall_height", 0))
        print(f"📐 Received dimensions: {wall_width} x {wall_height}", flush=True)

        eligible = get_eligible_texts(wall_width, wall_height)

        deduped = list({str(item): item for item in eligible}.values())
        print(f"🧾 Eligible mural count: {len(deduped)}")
        for i, mural in enumerate(deduped):
            print(f"{i+1}. {mural}", flush=True)

        return jsonify({"eligible": deduped})
    except Exception as e:
        print(f"❌ Error in /api/murals: {e}", flush=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/cdn-map", methods=["GET"])
def get_cdn_map():
    try:
        return jsonify(cdn_map)
    except Exception as e:
        print(f"❌ Error in /api/cdn-map: {e}", flush=True)
        return jsonify({"error": "Failed to load CDN map"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)