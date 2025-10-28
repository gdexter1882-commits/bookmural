import os
import re
import unicodedata
import json
import requests
from PIL import Image
from io import BytesIO

CDN_MAP_PATH = "cdn_map.json"
STATIC_ROOT = "static/previews"

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.lower().strip("-")

def draw_grid(handle, layout, output_dir, pages, cdn_map):
    cols, rows = map(int, layout["grid"].split("x"))
    pw = int(layout["page_w"] * 10)
    ph = int(layout["page_h"] * 10)
    margin_x = int(layout["margin_x"] * 10)
    margin_y = int(layout["margin_y"] * 10)
    gap = layout["row_gap"] * 10

    grid_w = cols * pw
    grid_h = rows * ph + (rows - 1) * gap
    canvas_w = grid_w + 2 * margin_x
    canvas_h = grid_h + 2 * margin_y

    img = Image.new("RGB", (canvas_w, canvas_h), "white")

    for idx in range(pages):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * pw
        y = margin_y + row * (ph + gap)

        page_num = idx + 1
        rel_path = f"{handle}/page_{page_num:03}.jpg"
        url = cdn_map.get(rel_path)

        try:
            response = requests.get(url)
            page_img = Image.open(BytesIO(response.content)).convert("RGB")
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
            img.paste(page_img, (x, y))
        except Exception as e:
            print(f"⚠️ Failed to load {rel_path}: {e}", flush=True)
            blank = Image.new("RGB", (pw, ph), "white")
            img.paste(blank, (x, y))

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{slugify(handle)}_grid.png")
    img.save(out_path)
    print(f"✅ Saved: {out_path}")