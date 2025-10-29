# app.py
import os
import json
import io
from quart import Quart, request, jsonify, send_file
from quart_cors import cors
from eligible_texts import get_eligible_texts, try_layout, slugify
from generate_box_grid import draw_grid_image
import asyncio

app = Quart(__name__)
app = cors(app, allow_origin="*")          # same as Flask-CORS

CSV_PATH = "mural_master_regenerated.csv"

# ----------------------------------------------------------------------
# Load CDN map once at start-up
# ----------------------------------------------------------------------
try:
    with open("cdn_map.json", "r", encoding="utf-8") as f:
        cdn_map = json.load(f)
    print(f"Loaded cdn_map.json with {len(cdn_map)} entries", flush=True)
except Exception as e:
    cdn_map = {}
    print(f"Failed to load cdn_map.json: {e}", flush=True)


# ----------------------------------------------------------------------
# Simple health / index
# ----------------------------------------------------------------------
@app.route("/")
async def index():
    return "Mural API is running", 200

@app.route("/health")
async def health():
    return "OK", 200


# ----------------------------------------------------------------------
# /api/murals – unchanged (still sync, fine)
# ----------------------------------------------------------------------
@app.route("/api/murals", methods=["POST"])
async def get_murals():
    data = await request.get_json()
    wall_width = float(data.get("wall_width", 0))
    wall_height = float(data.get("wall_height", 0))
    print(f"Received dimensions: {wall_width} x {wall_height}", flush=True)

    eligible = get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH, cdn_map=cdn_map)

    deduped = list({str(item): item for item in eligible}.values())
    print(f"Eligible mural count: {len(deduped)}")
    return jsonify({"eligible": deduped})


# ----------------------------------------------------------------------
# /api/accurate-grid – returns a *dynamic* URL that points to the async endpoint
# ----------------------------------------------------------------------
@app.route("/api/accurate-grid", methods=["POST"])
async def accurate_grid():
    data = await request.get_json()
    handle = data.get("handle")
    wall_width = float(data.get("wall_width", 0))
    wall_height = float(data.get("wall_height", 0))

    print(f"Computing layout for {handle} at {wall_width} x {wall_height}", flush=True)

    eligible = get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH, cdn_map=cdn_map)
    mural = next((m for m in eligible if m["handle"] == handle), None)
    if not mural:
        return jsonify({"error": "Mural not found"}), 404

    layout = try_layout(wall_width, wall_height, mural["page_w"], mural["page_h"], mural["pages"])
    if not layout.get("eligible"):
        return jsonify({"error": "Layout not eligible"}), 400

    grid_url = f"/api/grid/{slugify(handle)}?w={wall_width}&h={wall_height}"
    return jsonify({"grid_url": grid_url})


# ----------------------------------------------------------------------
# /api/grid/<handle> – **ASYNC** image generator
# ----------------------------------------------------------------------
@app.route("/api/grid/<handle>")
async def serve_grid(handle):
    wall_width = float(request.args.get("w", 0))
    wall_height = float(request.args.get("h", 0))

    print(f"Generating grid for {handle} at {wall_width} x {wall_height}", flush=True)

    eligible = get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH, cdn_map=cdn_map)
    mural = next((m for m in eligible if m["handle"] == handle), None)
    if not mural:
        return jsonify({"error": "Mural not found"}), 404

    layout = try_layout(wall_width, wall_height, mural["page_w"], mural["page_h"], mural["pages"])
    if not layout.get("eligible"):
        return jsonify({"error": "Layout not eligible"}), 400

    # ---- ASYNC IMAGE CREATION ----
    img = await draw_grid_image(mural, layout, cdn_map)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return await send_file(buf, mimetype="image/png")


# ----------------------------------------------------------------------
# Run with Uvicorn (Render uses this command)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # When you run locally:
    #   uvicorn app:app --host 0.0.0.0 --port 5000
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)