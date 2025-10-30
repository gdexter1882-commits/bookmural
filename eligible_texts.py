import csv
import unicodedata
import re
import os 
import urllib.parse 

CSV_PATH = "mural_master_regenerated.csv"

# Get the public URL base from the environment
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL') 

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text.lower().strip("_")

def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
    """
    Finds the optimal layout (columns, rows, scale, margin, row_gap) 
    that fits the wall dimensions while keeping page scale between 95% and 105%.
    The outside margin must be between 5cm and 16cm, and the mural must be centered.
    """
    best_layout = {"eligible": False}

    # Loops through margin_test (5cm minimum required margin)
    for margin_test in range(5, 16):
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        # Loops through scale (95% to 105% required)
        for scale_pct in range(95, 106):
            scaled_pw = page_w * scale_pct / 100
            scaled_ph = page_h * scale_pct / 100

            # Loops through row_gap (1cm to 5cm required)
            for row_gap in range(1, 6):
                for cols in range(1, pages + 1):
                    rows = (pages + cols - 1) // cols

                    # Note: Horizontal gap is 0 (pages butt up)
                    mural_w = cols * scaled_pw
                    mural_h = rows * scaled_ph + (rows - 1) * row_gap

                    if mural_w <= usable_w and mural_h <= usable_h:
                        # Layout fits the usable area (which enforces the minimum 5cm margin)
                        
                        # Calculate the margins that actually fit the wall (symmetric for centering)
                        margin_x = (wall_w - mural_w) / 2
                        margin_y = (wall_h - mural_h) / 2
                        
                        # ENFORCE MAXIMUM MARGIN: Ensure margins do not exceed 16cm
                        if margin_x <= 16 and margin_y <= 16:
                            
                            # Optimization: Find the layout with the smallest total margin (best fit)
                            if not best_layout["eligible"] or (margin_x + margin_y) < (best_layout["margin_x"] + best_layout["margin_y"]):
                                best_layout = {
                                    "eligible": True,
                                    "scale_pct": scale_pct,
                                    "page_w": scaled_pw,
                                    "page_h": scaled_ph,
                                    "grid": f"{rows}x{cols}",
                                    "rows": rows,
                                    "cols": cols,
                                    "margin_x": margin_x, # Symmetric: Left margin = Right margin
                                    "margin_y": margin_y, # Symmetric: Top margin = Bottom margin
                                    "row_gap": row_gap
                                }

    return best_layout

def get_eligible_texts(wall_width, wall_height, csv_path, cdn_map):
    eligible = []
    
    if not os.path.exists(csv_path):
        print(f"⚠️ CSV file not found at: {csv_path}", flush=True)
        return eligible

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    handle = row['Handle']
                    title = row['Title']
                    pages = int(row['Pages'])
                    width_cm = float(row['Page Width (cm)'])
                    height_cm = float(row['Page Height (cm)'])

                    aspect_ratio = width_cm / height_cm

                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)

                    if layout.get("eligible"):
                        
                        slug = slugify(handle)

                        # --- COVER IMAGE URL FIX (V4 - Simple String Replacement) ---
                        if R2_PUBLIC_URL:
                            # 1. Start with the Title and remove the literal string " pages)"
                            # This handles: "Title... (235 pages)" -> "Title... (235"
                            intermediate_filename = title.replace(" pages)", ")")
                            
                            # 2. Construct the exact filename: "xTitle... (235).jpg"
                            cover_filename = f"x{intermediate_filename}.jpg"
                            
                            # 3. Print the exact filename (NOT URL-ENCODED) for debugging
                            print(f"🔎 EXPECTED R2 FILENAME: {cover_filename}", flush=True)

                            # 4. URL-encode the filename
                            encoded_filename = urllib.parse.quote(cover_filename)
                            
                            # 5. Final URL
                            cover_url = f"{R2_PUBLIC_URL}/covers/{encoded_filename}"
                            print(f"✅ Generated R2 Cover URL: {cover_url}", flush=True)
                        else:
                            # Fallback if R2_PUBLIC_URL is NOT set.
                            print("⚠️ R2_PUBLIC_URL environment variable is MISSING. Using Shopify fallback (image may not load).", flush=True)
                            cover_key = handle
                            cover_url = f"https://cdn.shopify.com/s/files/1/0960/9930/3717/files/x{cover_key}.jpg"
                        
                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slug,
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "cover_url": cover_url, 
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            "folder": title.rsplit(" (", 1)[0] + f" ({pages})",
                            "layout_details": layout 
                        })
                except Exception as e:
                    print(f"Skipping row due to data error: {e}", flush=True)
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)
    
    return eligible