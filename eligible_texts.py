import csv
import unicodedata
import re
import os 
import math

# --- Configuration (Set the R2 Base URL for Covers) ---
R2_COVERS_BASE_URL = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/covers"

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
    Finds the optimal layout (cols, rows, scale, row_gap) that fits the wall
    dimensions while keeping:
    1. Page scale between 95% and 105%.
    2. Horizontal pages butted up (no gap).
    3. Horizontal margins strictly between 5cm and 16cm.
    4. Vertical margins strictly between 5cm and 16cm.
    """
    best_layout = {"eligible": False}

    for scale_pct in range(95, 106):
        scaled_pw = page_w * scale_pct / 100
        scaled_ph = page_h * scale_pct / 100

        for row_gap in range(1, 4):  # Row gaps of 1, 2, or 3 cm
            for rows in range(1, 31): 
                cols = math.ceil(pages / rows)
                total_w_needed_butted = cols * scaled_pw
                butted_up_margin_x = (wall_w - total_w_needed_butted) / 2

                # Horizontal margin must be between 5cm and 16cm
                if not (5 <= butted_up_margin_x <= 16):
                    continue 

                total_h_needed = rows * scaled_ph + (rows - 1) * row_gap
                final_margin_y = (wall_h - total_h_needed) / 2

                # Must fit vertically
                if final_margin_y < 0:
                    break 

                # Vertical margin must be between 5cm and 16cm
                if 5 <= final_margin_y <= 16:
                    current_layout = {
                        "eligible": True,
                        "scale_pct": scale_pct,
                        "cols": cols,
                        "rows": rows,
                        "row_gap": row_gap,
                        "page_w": scaled_pw,
                        "page_h": scaled_ph,
                        "butted_up_margin_x": butted_up_margin_x,
                        "margin_y": final_margin_y
                    }
                    return current_layout

    return best_layout

def get_folder_key_from_title(title: str) -> str:
    """
    Generates the folder key by replacing '(NUM pages)' with ' (NUM)'.
    This logic is robust against varying whitespace before the parentheses.
    """
    folder_key_pattern = re.compile(r'\s*\((?P<count>\d+)\s*pages\)$') 
    folder_key = folder_key_pattern.sub(r' (\g<count>)', title)
    return folder_key.strip()

# --- Main Function ---

def get_eligible_texts(wall_width, wall_height, csv_path="mural_master_regenerated.csv", cdn_map=None):
    """
    Reads the CSV, applies layout constraints, and returns a list of eligible texts.
    """
    eligible = []

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
                        # --- Slug Generation ---
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

                        # --- Folder Key ---
                        folder_key = get_folder_key_from_title(title)

                        # --- Cover URL ---
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
                            "folder": folder_key,
                            "layout_details": layout 
                        })
                except Exception as e:
                    print(f"Skipping row due to data error or layout check failure: {e} in row: {row}", flush=True)

        print(f"Loaded {len(eligible)} eligible murals", flush=True)

    except Exception as e:
        print(f"❌ Failed to read CSV: {e}", flush=True)

    return eligible
