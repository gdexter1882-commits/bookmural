# app.py
import os
import json
import csv # <--- ADDED
from flask import Flask, request, jsonify
from flask_cors import CORS
# --- UPDATED IMPORTS ---
from eligible_texts import try_layout, slugify, get_folder_key_from_title
from generate_box_grid import draw_grid
# --- (Removed get_eligible_texts as it's not needed for the single page) ---
import asyncio
import traceback

os.environ["FLASK_RUN_HOST"] = "0.0.0.0"
os.environ["FLASK_RUN_PORT"] = os.environ.get("PORT", "5000")

app = Flask(__name__, static_folder="static")

# CORS setup is correct, allowing requests from smallestroom.com
CORS(app, resources={r"/api/*": {"origins": "https://smallestroom.com"}})

CSV_PATH = "mural_master_regenerated.csv"

# --- LOAD DATA AT STARTUP ---

# Load cdn_map.json once at startup
try:
    with open("cdn_map.json", "r", encoding="utf-8") as f:
        cdn_map = json.load(f)
    print(f"🗺️ Loaded cdn_map.json with {len(cdn_map)} entries", flush=True)
except Exception as e:
    cdn_map = {}
    print(f"⚠️ Failed to load cdn_map.json: {e}", flush=True)

# Load mural_master_regenerated.csv once at startup
try:
    mural_data_by_handle = {}
    with open(CSV_PATH, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            handle = row.get('Handle')
            if handle:
                mural_data_by_handle[handle] = row
    print(f"📚 Loaded {len(mural_data_by_handle)} murals from {CSV_PATH}", flush=True)
except Exception as e:
    mural_data_by_handle = {}
    print(f"⚠️ Failed to load {CSV_PATH}: {e}", flush=True)

# --- END OF DATA LOADING ---


@app.route("/")
def index():
    # --- FIX: Added 'pass' to provide an indented block ---
    # You can also restore: return "Mural API is running", 200
    pass

@app.route("/health")
def health():
    # --- FIX: Restored the original health check ---
    return jsonify({"status": "ok"}), 200

@app.route("/api/eligible-texts", methods=["POST"])
def get_texts():
    # This route remains for your main calculator page
# ... existing code ...
    # This is a full-scan, so we call the original function
    # NOTE: You could optimize this to use the pre-loaded CSV data
    # but for now we keep it as it was.
    from eligible_texts import get_eligible_texts
    eligible = get_eligible_texts(
# ... existing code ...
    return jsonify(eligible)


# === NEW ENDPOINT FOR PRODUCT PAGES ===
@app.route("/api/calculate-single-mural", methods=["POST"])
def calculate_single_mural():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        wall_width = float(data.get("wall_width"))
        wall_height = float(data.get("wall_height"))
        # Get the non-slugified handle from Shopify (e.g., "voltaire-candide-...")
        shopify_handle = data.get("handle")

        if not all([wall_width, wall_height, shopify_handle]):
            return jsonify({"error": "Missing required fields: handle, wall_width, wall_height"}), 400
        
        # Slugify the Shopify handle to match the CSV's handle format
        csv_handle = slugify(shopify_handle)

        # 1. Find the book in our pre-loaded data
        book_data = mural_data_by_handle.get(csv_handle)
        
        if not book_data:
            print(f"❌ Could not find book. Shopify Handle: '{shopify_handle}', Slugged: '{csv_handle}'", flush=True)
            return jsonify({"error": "Book data not found"}), 404

        # 2. Get book properties
        pages = int(book_data.get('Pages', 0))
        page_w = float(book_data.get('Page Width (cm)', 0))
        page_h = float(book_data.get('Page Height (cm)', 0))
        title = book_data.get('Title', '') # e.g., "Voltaire, Candide... (194 pages)"
        
        if not all([pages, page_w, page_h, title]):
            return jsonify({"error": "Incomplete book data"}), 500
        
        # 3. Run the layout logic
        print(f"Checking layout for '{csv_handle}'...", flush=True)
        layout = try_layout(wall_width, wall_height, page_w, page_h, pages)

        # 4. Check if it fits
        if not layout.get("eligible"):
            print("Layout ineligible.", flush=True)
            return jsonify({
                "fits": False,
                "message": "This text does not fit on your wall dimensions."
            })
        
        # 5. It fits! Generate the grid.
        print(f"Layout eligible. Generating grid for '{csv_handle}'...", flush=True)
        folder_key = get_folder_key_from_title(title)
        
        grid_url = asyncio.run(draw_grid(
            csv_handle, 
            layout, 
            folder_key,
            pages,
            cdn_map
        ))
        
        if grid_url:
            return jsonify({
                "fits": True,
                "grid_url": grid_url,
                "layout": layout
            })
        else:
            return jsonify({"error": "Fit, but failed to generate grid image"}), 500

    except Exception as e:
        print(f"❌ Critical Error in /api/calculate-single-mural: {e}\n{traceback.format_exc()}", flush=True)
        return jsonify({"error": f"Server error: {e}"}), 500
# === END OF NEW ENDPOINT ===


@app.route("/api/accurate-grid", methods=["POST"])
def generate_accurate_grid():
# ... existing code ...
        # Re-run eligibility and layout calculation
        # NOTE: This is slow. You could optimize this to use the
        # pre-loaded CSV data and 'try_layout' like the new endpoint.
        from eligible_texts import get_eligible_texts
        eligible = get_eligible_texts(
# ... existing code ...
        if not mural:
            # Need to get folder_key and pages from our pre-loaded data
            csv_handle = slugify(handle)
            book_data = mural_data_by_handle.get(csv_handle)
            if book_data:
                mural = {
                    "folder": get_folder_key_from_title(book_data.get('Title', '')),
                    "pages": int(book_data.get('Pages', 0))
                }
            else:
                return jsonify({"error": "Mural not found"}), 404
        
        # Try to find the layout if it wasn't passed
        if not layout:
# ... existing code ...
            # We can re-calculate the layout here
            book_data = mural_data_by_handle.get(csv_handle)
            layout = try_layout(
                wall_width, 
                wall_height, 
                float(book_data.get('Page Width (cm)', 0)),
                float(book_data.get('Page Height (cm)', 0)),
                int(book_data.get('Pages', 0))
            )
            if not layout or not layout.get("eligible"):
                 return jsonify({"error": "Layout details not found or not eligible"}), 400

        # Run the async draw_grid function, passing exactly 5 arguments
# ... existing code ...