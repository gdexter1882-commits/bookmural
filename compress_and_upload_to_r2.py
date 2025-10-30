import os
import boto3
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

# ✅ Cloudflare R2 credentials
R2_ACCESS_KEY = "2ae153703e0bfa298058a5916b148f02"
R2_SECRET_KEY = "6c89032c195dac0047a7c83287d3f08083738b7861d800e1005d448458a56eea"
R2_ENDPOINT = "https://3a166d1f20174deac8fb4ae74b35c1a0.r2.cloudflarestorage.com"
R2_BUCKET = "mediumresfacsimiles"

# ✅ Local source directory of low-res TIFFs
SOURCE_DIR = r"D:\csv\LowResFacsimiles"

# ✅ Initialize R2 session
session = boto3.session.Session()
s3 = session.client(
    service_name="s3",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    endpoint_url=R2_ENDPOINT,
)

def process_file(local_path):
    rel_path = os.path.relpath(local_path, SOURCE_DIR)
    r2_key = os.path.splitext(rel_path.replace("\\", "/"))[0] + ".jpg"

    try:
        with Image.open(local_path) as im:
            im = im.convert("RGB")
            buffer = BytesIO()
            im.save(buffer, format="JPEG", quality=70)
            buffer.seek(0)
            s3.put_object(
                Bucket=R2_BUCKET,
                Key=r2_key,
                Body=buffer.read(),
                ContentType="image/jpeg",
                ACL="public-read"
            )
            print(f"✅ Uploaded: {r2_key}")
    except Exception as e:
        print(f"❌ Failed: {local_path} → {e}")

def convert_and_upload_all():
    tif_files = []
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            if file.lower().endswith(".tif") or file.lower().endswith(".tiff"):
                tif_files.append(os.path.join(root, file))

    print(f"🚀 Starting upload of {len(tif_files)} files...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(process_file, tif_files)

if __name__ == "__main__":
    convert_and_upload_all()