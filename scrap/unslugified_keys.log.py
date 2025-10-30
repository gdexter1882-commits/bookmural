import boto3
import re

# === CONFIGURATION ===
R2_ACCESS_KEY_ID = "2ae153703e0bfa298058a5916b148f02"
R2_SECRET_ACCESS_KEY = "6c89032c195dac0047a7c83287d3f08083738b7861d800e1005d448458a56eea"
R2_ACCOUNT_ID = "3a166d1f20174deac8fb4ae74b35c1a0"
R2_BUCKET = "mediumresfacsimiles"

# === SETUP S3 CLIENT FOR CLOUDFLARE R2 ===
session = boto3.session.Session()
s3 = session.client(
    service_name="s3",
    region_name="auto",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

# === PATTERN TO IDENTIFY UNSLUGIFIED KEYS ===
unslug_pattern = re.compile(r"[A-Z]| |,|\(")

unslugified_keys = []
total_keys = 0

print(f"🔍 Scanning R2 bucket: {R2_BUCKET}")
paginator = s3.get_paginator("list_objects_v2")
pages = paginator.paginate(Bucket=R2_BUCKET)

for page in pages:
    for obj in page.get("Contents", []):
        key = obj["Key"]
        total_keys += 1
        if unslug_pattern.search(key):
            unslugified_keys.append(key)

print(f"\n✅ Found {len(unslugified_keys)} unslugified keys out of {total_keys} total objects")

# === SAVE TO FILE ===
with open("unslugified_keys.log", "w", encoding="utf-8") as f:
    for key in unslugified_keys:
        f.write(key + "\n")

print("📝 Saved unslugified_keys.log")