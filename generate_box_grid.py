# generate_box_grid.py — FINAL RECOMMENDED VERSION (with tiny fixes)
import re
import unicodedata
import aiohttp
import asyncio
from PIL import Image, ImageDraw
from io import BytesIO
from eligible_texts import slugify


def draw_error_tile(width: int, height: int, page_num: int) -> Image.Image:
    tile = Image.new("RGB", (width, height), "#eeeeee")
    draw = ImageDraw.Draw(tile)
    draw.text((width // 2 - 10, height // 2 - 10), f"X{page_num}", fill="red")
    return tile


async def fetch_image(session: aiohttp.ClientSession, url: str, timeout: int = 30) -> Image.Image | None:
    if not url:
        return None
    try:
        async with session.get(url, timeout=timeout) as resp:
            resp.raise_for_status()
            data = await resp.read()
            return Image.open(BytesIO(data)).convert("RGB")
    except Exception as e:
        print(f"Failed to fetch {url}: {e}", flush=True)
        return None


async def draw_grid_image(mural: dict, layout: dict, cdn_map: dict) -> Image.Image:
    folder = mural["folder"]
    pages = mural["pages"]
    rows, cols = map(int, layout["grid"].split("x"))

    # Canvas setup
    pw = int(layout["page_w"] * 10)
    ph = int(layout["page_h"] * 10)
    margin_x = int(layout["margin_x"] * 10)
    margin_y = int(layout["margin_y"] * 10)
    gap = layout["row_gap"] * 10

    canvas_w = cols * pw + 2 * margin_x
    canvas_h = rows * ph + (rows - 1) * gap + 2 * margin_y
    img = Image.new("RGB", (canvas_w, canvas_h), "white")

    # Build URLs
    page_urls = []
    for i in range(pages):
        rel_path = f"{folder}/Page_{i+1:03}.jpg"
        url = cdn_map.get(rel_path)
        if not url:
            print(f"CDN map missing: {rel_path}", flush=True)
        page_urls.append(url)

    # Async fetch
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_image(session, url) for url in page_urls]
        fetched_images = await asyncio.gather(*tasks)

    success = sum(1 for im in fetched_images if im is not None)
    print(f"Fetched {success}/{pages} pages", flush=True)

    # Paste
    for idx, page_img in enumerate(fetched_images):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * pw
        y = margin_y + row * (ph + gap)

        if page_img:
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
        else:
            page_img = draw_error_tile(pw, ph, idx + 1)

        img.paste(page_img, (x, y))

    return img