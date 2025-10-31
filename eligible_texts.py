# eligible_texts.py
import csv
import unicodedata
import re
import os 
import math

# --- Configuration (Set the R2 Base URL for Covers) ---
R2_COVERS_BASE_URL = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/covers"

# --- Utility Functions ---\

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # This step removes non-word characters like commas and parentheses
    text = re.sub(r"[^\w\s-]", "", text)
    # This step replaces spaces/multiple hyphens with an underscore
    text = re.sub(r"[\s-]+\s*", "_", text)
    return text.lower().strip("_")

def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
# ... (try_layout function remains unchanged) ...
    best_layout = {"eligible": False}

    for margin_test in range(5, 16):
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        for scale_pct in range(95, 106):
            scaled_pw = page_w * scale_pct / 100
            scaled_ph = page_h * scale_pct / 100

            for row_gap in range(1, 4):
                # Calculate max possible rows/cols for the current scale and gap
                max_rows = math.floor(usable_h / (scaled_ph + row_gap))
                
                # If we can't fit at least 1 row, continue
                if max_rows < 1:
                    continue

                # Calculate columns required for the total number of pages
                cols = math.ceil(pages / max_rows)
                
                # Calculate total width required for this layout
                total_w_needed = cols * scaled_pw + (cols - 1) * row_gap
                
                # Check if the total width fits the usable wall width
                if total_w_needed <= usable_w:
                    # We found a valid layout that fits!
                    
                    # Calculate the average column gap (including the margins)
                    col_gap = (usable_w - cols * scaled_pw) / (cols - 1 if cols > 1 else 2) 

                    # Re-check the column gap constraint (must be close to row_gap, e.g., within 2cm)
                    if abs(col_gap - row_gap) <= 2 or cols == 1:
                        
                        # Calculate the margin needed to center the grid perfectly
                        # Horizontal margin (left/right)
                        final_margin_x = (wall_w - (cols * scaled_pw + (cols - 1) * row_gap)) / 2
                        # Vertical margin (top/bottom)
                        final_margin_y = (wall_h - (max_rows * scaled_ph + (max_rows - 1) * row_gap)) / 2

                        current_layout = {
                            "eligible": True,
                            "scale_pct": scale_pct,
                            "cols": cols,
                            "rows": max_rows,
                            "row_gap": row_gap,
                            "margin_x": final_margin_x,
                            "margin_y": final_margin_y,
                            "page_w": scaled_pw,
                            "page_h": scaled_ph
                        }

                        # Since we check scale_pct from 95 up to 105, the first valid layout found is the most suitable
                        return current_layout
                        
    return best_layout


# --- Main Function ---

def get_eligible_texts(wall_width, wall_height, csv_path="mural_master_regenerated.csv", cdn_map=None):
    """
    Reads the CSV, applies layout constraints, and returns a list of eligible texts.
    """
    eligible = []
    
    # Check for the CSV file
    if not os.path.exists(csv_path):
        print(f"❌ Critical Error: CSV file not found at {csv_path}", flush=True)
        return []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    title = row['Title']
                    handle = row['Handle'] 
                    pages = int(row['Pages'])
                    width_cm = float(row['Page Width (cm)'])
                    height_cm = float(row['Page Height (cm)'])
                    
                    aspect_ratio = height_cm / width_cm

                    # 1. Try to find a valid layout
                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)
                    
                    if layout["eligible"]:
                        
                        # --- FIX START: Robust slug generation (path removal + number preservation) ---
                        title_for_slug = title.strip()
                        
                        # 1. Remove author/stories path prefix (e.g., "Dickens, Charles, stories/")
                        if '/' in title_for_slug:
                            title_for_slug = title_for_slug.split('/', 1)[1].strip()
                            
                        # 2. Extract the page number from the end (e.g., '42' from '(42 pages)')
                        page_match = re.search(r'\((\d+)\s*pages\)$', title_for_slug)
                        page_number = page_match.group(1) if page_match else None
                            
                        # 3. Remove the entire '(XXX pages)' suffix from the title
                        title_for_slug_clean = re.sub(r'\s*\(\d+\s*pages\)$', '', title_for_slug)

                        # 4. Generate the base slug from the clean title
                        base_slug = slugify(title_for_slug_clean).replace('_', '-')
                        
                        # 5. Append the page number to the clean slug if found
                        if page_number:
                            clean_url_slug = f"{base_slug}-{page_number}"
                        else:
                            clean_url_slug = base_slug
                        # --- FIX END ---
                        
                        # --- Cover URL Logic (Fixed to use R2 URL) ---
                        cover_key = handle 
                        cover_url = f"{R2_COVERS_BASE_URL}/x{cover_key}.jpg"
                        
                        # Diagnostic print for the final URL
                        print(f"✅ Generated R2 Cover URL: {cover_url}", flush=True)

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "product_slug": clean_url_slug, # <-- NEW, CORRECT SLUG FIELD
                            "scale": layout.get("scale_pct"),
                            "cover_url": cover_url, 
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            # The folder name is used as the key for page images in cdn_map.json
                            "folder": title.rsplit(" (", 1)[0] + f" ({pages})", 
                            "layout_details": layout 
                        })
                except Exception as e:
                    print(f"Skipping row due to data error or layout check failure: {e} in row: {row}", flush=True)
        
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
        
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)
    
    return eligible