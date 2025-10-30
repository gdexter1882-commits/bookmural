# app.py
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from eligible_texts import get_eligible_texts, try_layout, slugify
from generate_box_grid import draw_grid
import asyncio # NEW

os.environ["FLASK_RUN_HOST"] = "0.0.0.0"
os.environ["FLASK_RUN_PORT"] = os.environ.get("PORT", "5000")

app = Flask(__name__, static_folder="static")

# CRITICAL FIX: Explicitly set the allowed origin to resolve the CORS error
CORS(app, resources={r"/api/*": {"origins": "https://smallestroom.com"}})

CSV_PATH = "mural_master_regenerated.csv" # Kept original path

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

        if wall_width <= 0 or wall_height <= 0:
            return jsonify({"error": "Invalid dimensions"}), 400

        eligible = get_eligible_texts(
            wall_width,
            wall_height,
            csv_path=CSV_PATH,
            cdn_map=cdn_map
        )
        return jsonify({"eligible": eligible})
    except Exception as e:
        print(f"❌ Error in /api/murals: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

@app.route("/api/accurate-grid", methods=["POST"])
def accurate_grid():
    try:
        data = request.get_json()
        handle = data.get("handle")
        # NOTE: wall dimensions are not strictly needed here if layout is provided, but kept for robustness
        wall_width = float(data.get("wall_width", 0))
        wall_height = float(data.get("wall_height", 0))

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

        # Run the async draw_grid function to generate and upload the image to R2
        grid_url = asyncio.run(draw_grid(
            handle, 
            layout, 
            mural["folder"], # FIX: Pass the folder name
            None, # output_dir argument (still required for function signature, but unused)
            mural["pages"], 
            cdn_map
        ))
        
        if grid_url:
            # Return the CDN URL directly
            return jsonify({"grid_url": grid_url})
        else:
            return jsonify({"error": "Failed to generate or upload grid"}), 500
            
    except Exception as e:
        print(f"❌ Error in /api/accurate-grid: {e}", flush=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host=os.environ["FLASK_RUN_HOST"], port=int(os.environ["FLASK_RUN_PORT"]))