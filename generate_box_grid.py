# generate_box_grid.py
import aiohttp
import asyncio
import boto3  
import os     
from PIL import Image, ImageDraw
from io import BytesIO
from eligible_texts import slugify 

# --- Configuration ---
PREVIEW_SCALE_FACTOR = 10 

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

# --- R2 Upload Function (HTTPS FIX APPLIED) ---
def upload_to_r2(handle: str, image: Image.Image) -> str:
    """Saves the Pillow image to a BytesIO buffer and uploads it to R2/S3."""
    try:
        R2_ENDPOINT = os.environ.get('R2_ENDPOINT_URL')
        BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
        
        if not R2_ENDPOINT or not BUCKET_NAME:
            print("❌ R2 environment variables not set. Image generation will fail.", flush=True)
            return "" 

        s3 = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT,
            region_name='auto' 
        )
        
        filename = f"{slugify(handle)}_grid.png"
        
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)

        s3.upload_fileobj(
            img_byte_arr,
            Bucket=BUCKET_NAME,
            Key=f"previews/{filename}",
            ExtraArgs={
                'ContentType': 'image/png',
                'ACL': 'public-read' 
            }
        )
        
        # Construct the public URL 
        # 1. Clean up the endpoint to use the public .r2.dev domain
        url_base = R2_ENDPOINT.replace('cloudflarestorage.com', 'r2.dev')
        # 2. Strip any protocol if present
        url_base = url_base.replace('http://', '').replace('https://', '')
        
        # 3. CRITICAL FIX: Explicitly prepend 'https://'
        public_url = f"https://{url_base}/{BUCKET_NAME}/previews/{filename}"
        
        print(f"☁️ Uploaded grid to R2: {public_url}", flush=True)
        return public_url

    except Exception as e:
        print(f"❌ R2 Upload Failed with Boto3 error: {e}", flush=True)
        return ""


async def draw_grid_image(mural: dict, layout: dict, cdn_map: dict) -> Image.Image:
    folder = mural["folder"]
    pages = mural["pages"]
    rows, cols = map(int, layout["grid"].split("x"))

    # Scale dimensions for preview
    pw = int(layout["page_w"] * PREVIEW_SCALE_FACTOR)
    ph = int(layout["page_h"] * PREVIEW_SCALE_FACTOR)
    margin_x = int(layout["margin_x"] * PREVIEW_SCALE_FACTOR)
    margin_y = int(layout["margin_y"] * PREVIEW_SCALE_FACTOR)
    gap = layout["row_gap"] * PREVIEW_SCALE_FACTOR

    # Canvas setup
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

    success_count = sum(1 for im in fetched_images if im)
    print(f"🧩 Successfully fetched {success_count} of {len(fetched_images)} pages", flush=True)

    # Paste images into grid
    for idx, page_img in enumerate(fetched_images):
        col = idx % cols
        row = idx // cols
        x = margin_x + col * (pw + gap)
        y = margin_y + row * (ph + gap)

        page_num = idx + 1
        
        if page_img:
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
        else:
            page_img = draw_error_tile(pw, ph, page_num)
            
        img.paste(page_img, (x, y))

    return img


# --- Main entry point for grid generation (5 arguments) ---
async def draw_grid(handle: str, layout: dict, folder: str, pages: int, cdn_map: dict):
    """Generates the grid image and uploads it to R2."""
    mural = {
        "folder": folder, 
        "pages": pages,
        "page_w": layout["page_w"],
        "page_h": layout["page_h"],
    }
    
    # Generate the Pillow Image object
    img_grid = await draw_grid_image(mural, layout, cdn_map)
    
    # Upload to R2 and return the CDN URL
    return upload_to_r2(handle, img_grid)