import csv
import unicodedata
import re

CSV_PATH = "mural_master_regenerated.csv"

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.lower().strip("-")

def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
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
                        margin_x = (wall_w - mural_w) / 2
                        margin_y = (wall_h - mural_h) / 2

                        if not (5 <= margin_x <= 15 and 5 <= margin_y <= 15):
                            continue

                        return {
                            "eligible": True,
                            "grid": f"{rows}x{cols}",
                            "scale_pct": scale_pct,
                            "row_gap": row_gap,
                            "margin_x": round(margin_x, 2),
                            "margin_y": round(margin_y, 2),
                            "page_w": round(scaled_pw, 2),
                            "page_h": round(scaled_ph, 2),
                            "text_centered": True
                        }

    return {"eligible": False}

def get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH, cdn_map=None):
    eligible = []

    try:
        with open(csv_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    handle = str(row.get("Handle", "")).strip()
                    title = str(row.get("Title", "")).strip()
                    pages = int(row.get("Pages", 0))
                    width_cm = float(row.get("Page Width (cm)", 0))
                    height_cm = float(row.get("Page Height (cm)", 0))

                    if height_cm == 0:
                        continue

                    aspect_ratio = round(width_cm / height_cm, 4)
                    layout = try_layout(wall_width, wall_height, width_cm, height_cm, pages)

                    if layout.get("eligible"):
                        # Match slugified handle to unslugified key in cdn_map
                        thumbnail_url = next(
                            (url for key, url in cdn_map.items()
                             if key.endswith("Page_001.jpg") and slugify(key.split("/")[0]) == handle),
                            None
                        )

                        if not thumbnail_url:
                            print(f"⚠️ Thumbnail not found in cdn_map for slugified handle: {handle}", flush=True)

                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "thumbnail": thumbnail_url or "",
                            "pages": pages,
                            "aspect_ratio": aspect_ratio,
                            "page_w": width_cm,
                            "page_h": height_cm
                        })
                except Exception as e:
                    print(f"⚠️ Skipping row due to error: {e}", flush=True)
        print(f"📄 Reloaded {csv_path} with {len(eligible)} eligible entries", flush=True)
    except Exception as e:
        print(f"❌ Failed to load {csv_path}: {e}", flush=True)

    return eligible