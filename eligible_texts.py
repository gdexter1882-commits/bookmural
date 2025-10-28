import csv
import unicodedata
import re

CSV_PATH = "mural_master_regenerated.csv"
BASE_URL = "https://mediumresfacsimiles.r2.cloudflarestorage.com/thumbnails"

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.lower().strip("-")

def try_layout(wall_w, wall_h, page_w, page_h, pages):
    # Placeholder — replace with actual layout logic
    return {"eligible": True, "grid": "3x3", "scale_pct": 100}

def get_eligible_texts(wall_width, wall_height, csv_path=CSV_PATH):
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
                        thumbnail_url = f"{BASE_URL}/{handle}/page_001.jpg"
                        eligible.append({
                            "title": title,
                            "handle": handle,
                            "slug": slugify(handle),
                            "grid": layout.get("grid"),
                            "scale": layout.get("scale_pct"),
                            "thumbnail": thumbnail_url,
                            "pages": pages,
                            "aspect_ratio": aspect_ratio
                        })
                except Exception as e:
                    print(f"⚠️ Skipping row due to error: {e}", flush=True)
        print(f"📄 Reloaded {csv_path} with {len(eligible)} eligible entries", flush=True)
    except Exception as e:
        print(f"❌ Failed to load {csv_path}: {e}", flush=True)

    return eligible