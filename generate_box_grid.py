# generate_box_grid.py
import os
import re
import unicodedata
import requests
from PIL import Image, ImageDraw
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from eligible_texts import slugify  # For consistency
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def draw_error_tile(width, height, page_num):
    tile = Image.new("RGB", (width, height), "#eeeeee")
    draw = ImageDraw.Draw(tile)
    draw.text((width // 2 - 10, height // 2 - 10), f"X{page_num}", fill="red")
    return tile

def fetch_image(url, timeout=30):
    if not url:
        return None
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}", flush=True)
        return None

def draw_grid_image(mural, layout, cdn_map):
    handle = mural["handle"]
    pages = mural["pages"]
    folder = mural["folder"]
    rows, cols = map(int, layout["grid"].split("x"))  # rows first
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

    # Build list of exact URLs using folder
    page_urls = []
    for idx in range(pages):
        page_num = idx + 1
        rel_path = f"{folder}/Page_{page_num:03}.jpg"  # Exact key match (capital P, 001)
        url = cdn_map.get(rel_path)
        if url is None:
            print(f"⚠️ CDN map missing: {rel_path}", flush=True)
        page_urls.append(url)

    # Fetch images in parallel with reduced workers
    with ThreadPoolExecutor(max_workers=4) as executor:
        fetched_images = list(executor.map(fetch_image, page_urls))

    success_count = sum(1 for img in fetched_images if img)
    print(f"🧩 Successfully fetched {success_count} of {len(fetched_images)} pages", flush=True)

    # Paste images into grid
    for idx in range(pages):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * pw
        y = margin_y + row * (ph + gap)

        page_img = fetched_images[idx]
        if page_img:
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
        else:
            page_img = draw_error_tile(pw, ph, idx + 1)

        img.paste(page_img, (x, y))

    return img  # Return the PIL Image instead of saving