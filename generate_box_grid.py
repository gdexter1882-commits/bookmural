# generate_box_grid.py
import os
import re
import unicodedata
import aiohttp
import asyncio
from PIL import Image, ImageDraw
from io import BytesIO
from eligible_texts import slugify  # For consistency

def draw_error_tile(width, height, page_num):
    tile = Image.new("RGB", (width, height), "#eeeeee")
    draw = ImageDraw.Draw(tile)
    draw.text((width // 2 - 10, height // 2 - 10), f"X{page_num}", fill="red")
    return tile

async def fetch_image(session, url, timeout=30):
    if not url:
        return None
    try:
        async with session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            content = await response.read()
            return Image.open(BytesIO(content)).convert("RGB")
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}", flush=True)
        return None

async def draw_grid_image(mural, layout, cdn_map):
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

    # Fetch images asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, url) for url in page_urls]
        fetched_images = await asyncio.gather(*tasks)

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