import os
import re
import time
import unicodedata
import requests
from PIL import Image
from io import BytesIO

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
    rows, cols = map(int, layout["grid"].split("x"))  # ✅ Corrected: rows first
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

    print(f"⏱️ Starting image fetch and paste for {pages} pages", flush=True)
    t0 = time.time()

    for idx in range(pages):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * pw
        y = margin_y + row * (ph + gap)

        page_num = idx + 1
        rel_path = f"{handle}/page_{page_num:03}.jpg"

        # 🔍 Match by suffix
        url = next((v for k, v in cdn_map.items() if k.endswith(rel_path)), None)

        print(f"🔍 Looking for {rel_path} in cdn_map", flush=True)

        if url is None:
            print(f"⚠️ CDN map missing: {rel_path}", flush=True)

        try:
            fetch_start = time.time()
            response = requests.get(url)
            fetch_time = time.time() - fetch_start

            page_img = Image.open(BytesIO(response.content)).convert("RGB")
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
            img.paste(page_img, (x, y))
            print(f"✅ Loaded page {page_num:03} in {fetch_time:.2f}s", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to load {rel_path}: {e}", flush=True)
            blank = Image.new("RGB", (pw, ph), "white")
            img.paste(blank, (x, y))

    print(f"⏱️ Total fetch + paste time: {time.time() - t0:.2f}s", flush=True)

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{slugify(handle)}_grid.png")

    print("⏱️ Saving image...", flush=True)
    t2 = time.time()
    img.save(out_path)
    print(f"✅ Saved: {out_path} ({time.time() - t2:.2f}s)", flush=True)