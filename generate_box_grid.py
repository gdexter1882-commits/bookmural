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
# ... (draw_error_tile function remains unchanged) ...
    tile = Image.new("RGB", (width, height), "#eeeeee")
    draw = ImageDraw.Draw(tile)
    draw.text((width // 2 - 10, height // 2 - 10), f"X{page_num}", fill="red")
    return tile

async def fetch_image(session: aiohttp.ClientSession, url: str, timeout: int = 30) -> Image.Image | None:
# ... (fetch_image function remains unchanged) ...
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

# --- R2 Upload Function (remains unchanged) ---
def upload_to_r2(handle: str, image: Image.Image) -> str:
# ... (upload_to_r2 function remains unchanged) ...
    try:
        R2_ENDPOINT = os.environ.get('R2_ENDPOINT_URL')
        BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
        R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL') 
        
        if not R2_ENDPOINT or not BUCKET_NAME or not R2_PUBLIC_URL:
            print("❌ R2 environment variables (R2_ENDPOINT_URL, R2_BUCKET_NAME, or R2_PUBLIC_URL) not set. Image generation will fail.", flush=True)
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
        
        public_url = f"{R2_PUBLIC_URL}/previews/{filename}"
        
        print(f"☁️ Uploaded grid to R2: {public_url}", flush=True)
        return public_url

    except Exception as e:
        print(f"❌ R2 Upload Failed with Boto3 error: {e}", flush=True)
        raise 

async def draw_grid_image(mural: dict, layout: dict, cdn_map: dict) -> Image.Image:
    folder = mural["folder"]
    pages = mural["pages"]
    
    # Use 'rows' and 'cols' keys directly from the layout dict
    rows = int(layout["rows"])
    cols = int(layout["cols"])

    # Scale dimensions for preview. These must be integers.
    pw = int(layout["page_w"] * PREVIEW_SCALE_FACTOR)
    ph = int(layout["page_h"] * PREVIEW_SCALE_FACTOR)
    
    # FIX: Use the new, pre-calculated butted-up margin
    effective_margin_x = int(layout["butted_up_margin_x"] * PREVIEW_SCALE_FACTOR)
    
    # The margin_y remains the same (calculated with vertical gaps)
    margin_y = int(layout["margin_y"] * PREVIEW_SCALE_FACTOR)
    
    # The calculated gap (used for vertical spacing)
    gap = layout["row_gap"] * PREVIEW_SCALE_FACTOR 

    # Canvas setup - Calculated using the butted-up margin. This maintains proportional width.
    canvas_w = 2 * effective_margin_x + cols * pw
    
    # Vertical height calculation remains the same (it still needs the vertical gaps)
    canvas_h = rows * ph + (rows - 1) * gap + 2 * margin_y
    
    img = Image.new("RGB", (int(canvas_w), int(canvas_h)), "white") 

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
        
        # New X: Pages butt up, starting from the effective margin. No gap added here.
        x = int(effective_margin_x + col * pw)
        
        # Vertical placement: Still uses the gap. Cast to int().
        y = int(margin_y + row * (ph + gap))

        page_num = idx + 1
        
        if page_img:
            # Note: LANCZOS is the highest quality resampling filter
            page_img = page_img.resize((pw, ph), Image.LANCZOS)
        else:
            page_img = draw_error_tile(pw, ph, page_num)
            
        img.paste(page_img, (x, y))

    return img


# --- Main entry point for grid generation (5 arguments) ---
async def draw_grid(handle: str, layout: dict, folder: str, pages: int, cdn_map: dict):
# ... (draw_grid function remains unchanged) ...
    mural = {
        "folder": folder, 
        "pages": pages,
        "page_w": layout["page_w"],
        "page_h": layout["page_h"],
    }
    
    img_grid = await draw_grid_image(mural, layout, cdn_map)
    
    return upload_to_r2(handle, img_grid)