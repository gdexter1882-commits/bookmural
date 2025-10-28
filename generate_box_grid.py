import os
import json
import time
import requests
from PIL import Image, ImageDraw
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from eligible_texts import slugify

def draw_error_tile(width, height, page_num):
    tile = Image.new("RGB", (width, height), "#eeeeee")
    draw = ImageDraw.Draw(tile)
    draw.text((width // 2 - 10, height // 2 - 10), f"X{page_num}", fill="red")
    return tile

def fetch_image(url, timeout=6):
    try:
        response = requests.get(url, timeout=timeout)
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}", flush=True)
        return None

def draw_grid(layout, output_dir, cdn_map):
    handle = layout["handle"]
    pages = layout["pages"]
    pw = int(layout["page_w"] * 5)
    ph = int(layout["page_h"] * 5)
    margin_x = int(layout["margin_x"] * 5)
    margin_y = int(layout["margin_y"] * 5)
    gap = layout["row_gap"] * 5

    cols = layout["cols"]
    rows = layout["rows"]
    canvas_w = cols * pw + (cols - 1) * gap + 2 * margin_x
    canvas_h = rows * ph + (rows - 1) * gap + 2 * margin_y

    img = Image.new("RGB", (canvas_w, canvas_h), "white")

    # Build list of URLs
    page_urls = [cdn_map.get(page["rel_path"]) for page in pages]

    print(f"⏱️ Starting image fetch for {len(page_urls)} pages", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        fetched_images = list(executor.map(lambda url: fetch_image(url) if url else None, page_urls))
    print(f"⏱️ Fetching took {time.time() - t0:.2f}s", flush=True)

    success_count = sum(1 for img in fetched_images if img)
    print(f"🧩 Successfully fetched {success_count} of {len(fetched_images)} pages", flush=True)

    print("⏱️ Starting resize and paste", flush=True)
    t1 = time.time()
    for idx, page in enumerate(pages):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * (pw + gap)
        y = margin_y + row * (ph + gap)

        page_img = fetched_images[idx]
        if page_img:
            page_img = page_img.resize((pw, ph), Image.BILINEAR)
        else:
            page_img = draw_error_tile(pw, ph, idx + 1)

        img.paste(page_img, (x, y))
    print(f"⏱️ Resize and paste took {time.time() - t1:.2f}s", flush=True)

    filename = f"{slugify(handle)}_grid.png"
    out_path = os.path.join(output_dir, filename)

    print("⏱️ Saving image...", flush=True)
    t2 = time.time()
    try:
        img.save(out_path)
        print(f"✅ Grid saved: {out_path} ({time.time() - t2:.2f}s)", flush=True)
    except Exception as e:
        print(f"❌ Failed to save grid: {e}", flush=True)