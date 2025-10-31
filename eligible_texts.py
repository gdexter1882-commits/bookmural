# eligible_texts.py
import csv
import unicodedata
import re
import os 
import math

# --- Configuration (Set the R2 Base URL for Covers) ---
R2_COVERS_BASE_URL = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/covers"

# --- Utility Functions ---

def slugify(text):
# ... (slugify function remains unchanged) ...
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+\s*", "_", text)
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

            for row_gap in range(1, 4):
                # Calculate max possible rows/cols for the current scale and gap
                max_rows = math.floor(usable_h / (scaled_ph + row_gap))
                
                # If we can't fit at least 1 row, continue
                if max_rows < 1:
                    continue

                # Calculate columns required for the total number of pages
                cols = math.ceil(pages / max_rows)
                
                # Calculate total width required for this layout (PAGES + GAPS)
                total_w_needed = cols * scaled_pw + (cols - 1) * row_gap
                
                # Check if the total width fits the usable wall width
                if total_w_needed <= usable_w:
                    # We found a valid layout that fits!
                    
                    # Calculate the average column gap (including the margins)
                    col_gap = (usable_w - cols * scaled_pw) / (cols - 1 if cols > 1 else 2) 

                    # Re-check the column gap constraint (must be close to row_gap, e.g., within 2cm)
                    if abs(col_gap - row_gap) <= 2 or cols == 1:
                        
                        # Calculate the margin needed to center the grid perfectly (MARGIN AROUND PAGES+GAPS)
                        final_margin_x = (wall_w - (cols * scaled_pw + (cols - 1) * row_gap)) / 2
                        final_margin_y = (wall_h - (max_rows * scaled_ph + (max_rows - 1) * row_gap)) / 2
                        
                        # --- FIX START: Calculate the margin for the butted-up grid ---
                        total_gap_space = (cols - 1) * row_gap
                        # The butted-up margin is the original margin plus half the total gap space
                        butted_up_margin_x = final_margin_x + (total_gap_space / 2)

                        # NEW CHECK: Ensure the BUTTED-UP margin is within the desired range (<= 16cm)
                        if butted_up_margin_x <= 16:
                            
                            current_layout = {
                                "eligible": True,
                                "scale_pct": scale_pct,
                                "cols": cols,
                                "rows": max_rows,
                                "row_gap": row_gap,
                                "margin_x": final_margin_x, 
                                "margin_y": final_margin_y,
                                "page_w": scaled_pw,
                                "page_h": scaled_ph,
                                # NEW FIELD: The effective horizontal margin for butted-up pages
                                "butted_up_margin_x": butted_up_margin_x 
                            }

                            # Since we check scale_pct from 95 up to 105, the first valid layout found is the most suitable
                            return current_layout
                        # --- FIX END ---
                        
    return best_layout


# --- Main Function (remains unchanged, it passes layout_details) ---

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
                        
                        # --- Slug Generation (remains unchanged) ---
                        title_for_slug = title.strip()
                        
                        if '/' in title_for_slug:
                            title_for_slug = title_for_slug.split('/', 1)[1].strip()
                            
                        page_match = re.search(r'\((\d+)\s*pages\)$', title_for_slug)
                        page_number = page_match.group(1) if page_match else None
                            
                        title_for_slug_clean = re.sub(r'\s*\(\d+\s*pages\)$', '', title_for_slug)

                        base_slug = slugify(title_for_slug_clean).replace('_', '-')
                        
                        if page_number:
                            clean_url_slug = f"{base_slug}-{page_number}"
                        else:
                            clean_url_slug = base_slug
                        # --- Slug Generation End ---
                        
                        # --- Cover URL Logic ---
                        cover_key = handle 
                        cover_url = f"{R2_COVERS_BASE_URL}/x{cover_key}.jpg"
                        
                        print(f"✅ Generated R2 Cover URL: {cover_url}", flush=True)

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "product_slug": clean_url_slug, 
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
                    print(f"Skipping row due to data error or layout check failure: {e} in row: {row}", flush=True)
        
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
        
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)
    
    return eligible