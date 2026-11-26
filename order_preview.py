"""
Storywalls – a preview picture for each mural in an order.

When a checkout is started, shopify_checkout.py asks this module for a picture URL for every mural
(the book's pages laid out exactly as they will be printed, with the 76 cm wallpaper drops dashed in
and the wall size written underneath). The URL is fixed straight away and saved on the order line as
the hidden property "_preview"; the picture itself is drawn and uploaded to R2 in a background thread,
so the checkout is not slowed down. The order-confirmation email shows it.

Uses the same R2 settings as generate_box_grid.py (R2_ENDPOINT_URL, R2_BUCKET_NAME, R2_PUBLIC_URL).
"""
import asyncio
import csv
import math
import os
import re
import threading
import uuid
from io import BytesIO

import aiohttp
import boto3
from PIL import Image, ImageDraw, ImageFont

from eligible_texts import slugify, get_folder_key_from_title
from generate_box_grid import fetch_image

DROP_W = 76
MAX_PX = 1000          # picture width in pixels at most
BAR_PX = 64            # caption strip under the wall


def _slug_for(title):
    """The Shopify product handle the calculator gives this CSV title (same steps as eligible_texts)."""
    t = title.strip()
    if '/' in t:
        t = t.split('/', 1)[1].strip()
    m = re.search(r'\((\d+)\s*pages\)$', t)
    base = slugify(re.sub(r'\s*\(\d+\s*pages\)$', '', t)).replace('_', '-')
    return f"{base}-{m.group(1)}" if m else base


_books = None


def book_for_handle(handle, csv_path="mural_master_regenerated.csv"):
    """(folder, pages) for a Shopify product handle, or None."""
    global _books
    if _books is None:
        books = {}
        try:
            with open(csv_path, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    books[_slug_for(row["Title"])] = (get_folder_key_from_title(row["Title"]), int(row["Pages"]))
        except Exception as e:
            print(f"⚠️ order_preview: could not read CSV: {e}", flush=True)
        _books = books
    return _books.get(handle)


def drops_text(wall_w):
    n = math.ceil(wall_w / DROP_W)
    last = round(wall_w - (n - 1) * DROP_W)
    if n == 1:
        return f"1 drop, 76 cm wide, trimmed to {wall_w} cm"
    return f"{n} drops, 76 cm wide" + (f" (last one {last} cm)" if last < DROP_W else "")


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


async def _draw(folder, pages, layout, wall_w, wall_h, cdn_map):
    s = min(4.0, MAX_PX / wall_w)                   # pixels per cm
    W, H = round(wall_w * s), round(wall_h * s)
    img = Image.new("RGB", (W + 2, H + 2 + BAR_PX), "white")
    d = ImageDraw.Draw(img)
    cols, rows = int(layout["cols"]), int(layout["rows"])
    pw, ph, gap = layout["page_w"] * s, layout["page_h"] * s, layout["row_gap"] * s
    mx, my = layout["butted_up_margin_x"] * s, layout["margin_y"] * s

    urls = [cdn_map.get(f"{folder}/Page_{i + 1:03}.jpg") for i in range(pages)]
    async with aiohttp.ClientSession() as session:
        ims = await asyncio.gather(*[fetch_image(session, u) for u in urls])
    for i, im in enumerate(ims):
        x, y = 1 + mx + (i % cols) * pw, 1 + my + (i // cols) * (ph + gap)
        x0, y0, x1, y1 = round(x), round(y), round(x + pw), round(y + ph)
        if im:
            img.paste(im.resize((max(1, x1 - x0), max(1, y1 - y0)), Image.LANCZOS), (x0, y0))
        else:
            d.rectangle([x0, y0, x1 - 1, y1 - 1], fill="#eeeeee")

    line = (70, 62, 55)
    k = 1
    while k * DROP_W < wall_w:                       # dashed drop lines
        x = 1 + round(k * DROP_W * s)
        y = 1
        while y < H:
            d.line([(x, y), (x, min(H, y + 9))], fill=line, width=2)
            y += 15
        k += 1
    d.rectangle([0, 0, W + 1, H + 1], outline=line, width=2)

    n = math.ceil(wall_w / DROP_W)
    f = _font(max(11, min(18, round(DROP_W * s / 4))))
    for i in range(n):                               # drop numbers along the top
        if (wall_w - i * DROP_W) * s < 24:
            continue
        cx = 1 + (i * DROP_W + min(DROP_W, wall_w - i * DROP_W) / 2) * s
        d.text((cx, 6), str(i + 1), fill=line, font=f, anchor="mt")
    cap = f"Your wall: {wall_w / 100:.2f} m x {wall_h / 100:.2f} m  |  {drops_text(wall_w)}, shown as dashed lines"
    d.text((W / 2, H + 2 + BAR_PX / 2), cap, fill=(40, 40, 40), font=_font(18 if W >= 700 else 14), anchor="mm")
    return img


def _upload(key, img):
    s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT_URL"], region_name="auto")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    s3.upload_fileobj(buf, Bucket=os.environ["R2_BUCKET_NAME"], Key=key,
                      ExtraArgs={"ContentType": "image/jpeg", "ACL": "public-read"})


_cdn = None


def _cdn_map():
    global _cdn
    if _cdn is None:
        try:
            import json
            with open("cdn_map.json", encoding="utf-8") as f:
                _cdn = json.load(f)
        except Exception as e:
            print(f"⚠️ order_preview: could not read cdn_map.json: {e}", flush=True)
            _cdn = {}
    return _cdn


def start_preview(handle, layout, wall_w, wall_h):
    """Returns the picture's URL at once (or None) and draws/uploads it in the background."""
    public = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")
    book = book_for_handle(handle)
    if not public or not os.environ.get("R2_ENDPOINT_URL") or not os.environ.get("R2_BUCKET_NAME") or not book:
        return None
    folder, pages = book
    key = f"previews/orders/{uuid.uuid4().hex}.jpg"

    def work():
        try:
            img = asyncio.run(_draw(folder, pages, layout, wall_w, wall_h, _cdn_map()))
            _upload(key, img)
            print(f"🖼️ Order preview uploaded: {key}", flush=True)
        except Exception as e:
            print(f"❌ Order preview failed for {handle} {wall_w}x{wall_h}: {e}", flush=True)

    threading.Thread(target=work, daemon=True).start()
    return f"{public}/{key}"
