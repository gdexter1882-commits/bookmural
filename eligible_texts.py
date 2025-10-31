import csv
import unicodedata
import re
import os 
import math

# --- Configuration (Set the R2 Base URL for Covers) ---
R2_COVERS_BASE_URL = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/covers"

# Regex to match and remove the trailing page count from the CSV title, e.g., ' (58 pages)'
# This regex matches the final page count pattern, including any number of preceding spaces.
CSV_TITLE_COUNT_REGEX = re.compile(r'\s*\(\d+\s*pages\)$')


# --- Utility Functions ---

def slugify(text):
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
    # DEFENSIVE INITIALIZATION: Ensure all required keys exist, even if not eligible.
    best_layout = {
        "eligible": False,
        "scale_pct": 0,
        "margin_x": 0,
        "margin_y": 0,
        "cols": 0,
        "rows": 0,
        "page_w_px": 0, 
        "page_h_px": 0,
        "row_gap_px": 0
    }

    for margin_test in range(5, 16):
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        for scale_pct in range(95, 106):
            scale = scale_pct / 100.0
            
            # Scaled page dimensions
            scaled_page_w = page_w * scale
            scaled_page_h = page_h * scale
            
            # Determine maximum possible columns and rows
            max_cols = max(1, math.floor(usable_w / scaled_page_w))
            max_rows = max(1, math.floor(usable_h / scaled_page_h))

            # Iterate over possible number of columns
            for cols in range(1, max_cols + 1):
                # Calculate required rows
                rows = math.ceil(pages / cols)
                
                if rows > max_rows:
                    continue
                    
                # Calculate total width required (no gap between columns)
                total_w = cols * scaled_page_w
                
                # Calculate total height required
                
                # Calculate row gap: The gap is distributed across rows-1 spaces.
                num_gaps = rows - 1 
                
                if num_gaps > 0:
                    # Calculate required row gap
                    total_h_no_gap = rows * scaled_page_h
                    remaining_h = usable_h - total_h_no_gap
                    row_gap = max(0, remaining_h / num_gaps)
                else:
                    row_gap = 0
                
                total_h = total_h_no_gap + num_gaps * row_gap
                
                # Final check for fit within usable area
                if total_w <= usable_w and total_h <= usable_h:
                    # This is an eligible layout.
                    
                    # Store details, prioritizing the smallest scale for the most compact fit
                    if not best_layout["eligible"] or scale_pct < best_layout["scale_pct"]:
                        best_layout = {
                            "eligible": True,
                            "scale_pct": scale_pct,
                            "margin_x": margin_test,
                            "margin_y": margin_test,
                            "cols": cols,
                            "rows": rows,
                            "page_w_px": scaled_page_w, # Stored as float for accuracy
                            "page_h_px": scaled_page_h, # Stored as float for accuracy
                            "row_gap_px": row_gap
                        }

    return best_layout


def get_eligible_texts(wall_width, wall_height, csv_path="mural_master_regenerated.csv", cdn_map=None):
    """
    Reads the CSV and filters texts that can fit the specified wall dimensions.
    Requires cdn_map for existence checks.
    """
    if cdn_map is None:
        cdn_map = {}
        print("⚠️ Warning: cdn_map is empty. Cannot check image existence.", flush=True)

    eligible = []
    
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

                    # Calculate aspect ratio
                    aspect_ratio = width_cm / height_cm

                    # 1. Try to find a layout that fits
                    # NOTE: try_layout is now defensively coded to prevent the KeyError: 'page_w'
                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)
                    
                    if layout['eligible']:
                        
                        # 2. GENERATE THE FOLDER KEY: Read directly from the new, perfect column.
                        # This is the safest way to get the correct folder name, including the extra spaces.
                        folder = row.get('CDN_Folder_Key')
                        
                        # Fallback for old/un-synced rows (should not be needed after synchronizer runs)
                        if not folder:
                            # Reverting to the old logic if the new column is missing
                            # We use .strip() here because it's the safest assumption for pre-synced data
                            folder_base = CSV_TITLE_COUNT_REGEX.sub('', title).strip() 
                            folder = f"{folder_base} ({pages})"
                        
                        # 3. Check for image existence (at least the first page)
                        first_page_key = f"{folder}/Page_001.jpg"
                        
                        if first_page_key not in cdn_map:
                            # This handles the case where the folder key is wrong or missing entirely
                            print(f"❌ Skipping {handle}: Missing key in CDN map: {first_page_key}", flush=True)
                            continue

                        # Determine the R2 cover URL
                        cover_key = handle 
                        cover_url = f"{R2_COVERS_BASE_URL}/x{cover_key}.jpg"
                        
                        # Diagnostic print for the final URL
                        # print(f"✅ Generated R2 Cover URL: {cover_url}", flush=True)

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "scale": layout.get("scale_pct"),
                            "cover_url": cover_url, 
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm,
                            # The folder name is used as the key for page images in cdn_map.json
                            "folder": folder, 
                            "layout_details": layout 
                        })
                except Exception as e:
                    print(f"Skipping row due to data error or layout check failure: {e} in row: {row}", flush=True)
        
        print(f"Loaded {len(eligible)} eligible murals", flush=True)
        
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)
    
    return eligible
