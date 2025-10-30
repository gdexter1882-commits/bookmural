# eligible_texts.py
import csv
import unicodedata
import re
import os # NEW: Import os for path handling

CSV_PATH = "mural_master_regenerated.csv"

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
    """
    best_layout = {"eligible": False}

    for margin_test in range(5, 16):
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        for scale_pct in range(95, 106):
            scaled_pw = page_w * scale_pct / 100
            scaled_ph = page_h * scale_pct / 100

            for row_gap in range(1, 6):
                for cols in range(1, pages + 1):
                    rows = (pages + cols - 1) // cols

                    mural_w = cols * scaled_pw
                    mural_h = rows * scaled_ph + (rows - 1) * row_gap

                    if mural_w <= usable_w and mural_h <= usable_h:
                        # Success: Layout fits
                        # Calculate the margins that actually fit the wall
                        margin_x = (wall_w - mural_w) / 2
                        margin_y = (wall_h - mural_h) / 2
                        
                        # Only update if the new margins are a better fit (i.e., smaller overall margin)
                        if not best_layout["eligible"] or (margin_x + margin_y) < (best_layout["margin_x"] + best_layout["margin_y"]):
                            best_layout = {
                                "eligible": True,
                                "scale_pct": scale_pct,
                                "page_w": scaled_pw,
                                "page_h": scaled_ph,
                                "grid": f"{rows}x{cols}",
                                "rows": rows,
                                "cols": cols,
                                "margin_x": margin_x,
                                "margin_y": margin_y,
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

                    # Calculate aspect_ratio
                    aspect_ratio = width_cm / height_cm

                    # Calculate layout
                    # Note: The try_layout function is the core layout algorithm.
                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)

                    if layout.get("eligible"):
                        
                        # --- Simplified Cover URL Logic (Proxy for new CSV) ---
                        # We use the entire handle as the cover_key, accepting potential 404s,
                        # which is more robust than the old fragile regex.
                        cover_key = handle 
                        cover_url = f"https://cdn.shopify.com/s/files/1/0960/9930/3717/files/x{cover_key}.jpg"

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "cover_url": cover_url, 
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            "folder": title.rsplit(" (", 1)[0] + f" ({pages})",
                            # Add layout details to the initial response for potential frontend use
                            "layout_details": layout 
                        })
                except Exception as e:
                    print(f"Skipping row due to data error: {e}", flush=True)
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)
    
    return eligible