# app.py (modified to add /api/check-mural endpoint)
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from eligible_texts import get_eligible_texts, try_layout, slugify
from generate_box_grid import draw_grid
import asyncio
import traceback # <--- ADDED THIS LINE

os.environ["FLASK_RUN_HOST"] = "0.0.0.0"
os.environ["FLASK_RUN_PORT"] = os.environ.get("PORT", "5000")

app = Flask(__name__, static_folder="static")

# CORS setup is correct, allowing requests from smallestroom.com
CORS(app, resources={r"/api/*": {"origins": "https://smallestroom.com"}})

CSV_PATH = "mural_master_regenerated.csv"

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
        wall_width = data.get("wall_width", 0)
        wall_height = data.get("wall_height", 0)
        
        if not wall_width or not wall_height:
            return jsonify({"error": "Missing wall dimensions"}), 400

        eligible = get_eligible_texts(
            wall_width,
            wall_height,
            csv_path=CSV_PATH,
            cdn_map=cdn_map
        )
        return jsonify(eligible)

    except Exception as e:
        print(f"❌ Error in /api/murals: {e}", flush=True)
        traceback.print_exc() # Print traceback for murals endpoint too, just in case
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/check-mural", methods=["POST"])
def check_mural():
    try:
        data = request.get_json()
        handle = data.get("handle")
        wall_width = data.get("wall_width", 0)
        wall_height = data.get("wall_height", 0)
        
        if not handle or not wall_width or not wall_height:
            return jsonify({"error": "Missing parameters"}), 400

        eligible = get_eligible_texts(
            wall_width,
            wall_height,
            csv_path=CSV_PATH,
            cdn_map=cdn_map
        )
        mural = next((m for m in eligible if m["handle"] == handle), None)
        
        if mural:
            return jsonify(mural)
        else:
            return jsonify({"eligible": False})

    except Exception as e:
        print(f"❌ Error in /api/check-mural: {e}", flush=True)
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/accurate-grid", methods=["POST"])
def accurate_grid():
    try:
        data = request.get_json()
        handle = data.get("handle")
        wall_width = data.get("wall_width", 0)
        wall_height = data.get("wall_height", 0)
        
        if not handle or not wall_width or not wall_height:
            return jsonify({"error": "Missing handle or wall dimensions"}), 400

        print(f"🧮 Generating grid for {handle} at {wall_width} x {wall_height}", flush=True)

        # Re-run eligibility and layout calculation
        eligible = get_eligible_texts(
            wall_width,
            wall_height,
            csv_path=CSV_PATH,
            cdn_map=cdn_map
        )
        mural = next((m for m in eligible if m["handle"] == handle), None)
        if not mural:
            return jsonify({"error": "Mural not found"}), 404

        # Use the already calculated layout data
        layout = mural.get("layout_details")
        if not layout or not layout.get("eligible"):
             return jsonify({"error": "Layout details not found or not eligible"}), 400

        # Run the async draw_grid function, passing exactly 5 arguments
        grid_url = asyncio.run(draw_grid(
            handle, 
            layout, 
            mural["folder"],  # ARG 3: folder
            mural["pages"],   # ARG 4: pages
            cdn_map           # ARG 5: cdn_map
        ))
        
        if grid_url:
            # Return the CDN URL directly
            return jsonify({"grid_url": grid_url})
        else:
            return jsonify({"error": "Failed to generate or upload grid"}), 500
            
    except Exception as e:
        print(f"❌ Critical Error in /api/accurate-grid: {e}", flush=True)
        traceback.print_exc() # <--- MODIFIED: Print the full error stack
        return jsonify({"error": "Failed to generate or upload grid"}), 500