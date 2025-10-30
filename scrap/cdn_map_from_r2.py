import boto3
import json
import time
from collections import Counter

# === CONFIGURATION ===
R2_ACCESS_KEY_ID = "2ae153703e0bfa298058a5916b148f02"
R2_SECRET_ACCESS_KEY = "6c89032c195dac0047a7c83287d3f08083738b7861d800e1005d448458a56eea"
R2_ACCOUNT_ID = "3a166d1f20174deac8fb4ae74b35c1a0"
R2_BUCKET = "mediumresfacsimiles"

# ✅ Use Public Development URL for public access
R2_PUBLIC_BASE = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev"

# === SETUP S3 CLIENT FOR CLOUDFLARE R2 ===
session = boto3.session.Session()
s3 = session.client(
    service_name="s3",
    region_name="auto",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

# === BUILD CDN MAP ===
cdn_map = {}
version_token = int(time.time())
all_keys = []

print(f"🔍 Listing objects in R2 bucket: {R2_BUCKET}")
paginator = s3.get_paginator("list_objects_v2")
pages = paginator.paginate(Bucket=R2_BUCKET)

for page in pages:
    for obj in page.get("Contents", []):
        key = obj["Key"].replace("\\", "/")
        all_keys.append(key)

# === FILTER USING AUDIT LOGIC ===
valid_keys = [k for k in all_keys if k.lower().endswith(".jpg") and "page_" in k]
malformed_keys = [k for k in all_keys if k not in valid_keys]

# === BUILD MAP ===
for key in valid_keys:
    url = f"{R2_PUBLIC_BASE}/{key}?v={version_token}"
    cdn_map[key] = url

# === CHECK FOR DUPLICATES AND BAD URLS ===
key_counts = Counter(cdn_map.keys())
url_counts = Counter(cdn_map.values())
duplicate_keys = [k for k, v in key_counts.items() if v > 1]
duplicate_urls = [u for u, v in url_counts.items() if v > 1]
bad_urls = [u for u in cdn_map.values() if u.count("?v=") > 1]

# === SUMMARY ===
print(f"\n✅ Retained {len(cdn_map)} valid entries out of {len(all_keys)}")
print(f"🧹 Removed {len(malformed_keys)} malformed entries")
print(f"⚠️ Duplicate keys: {len(duplicate_keys)}")
print(f"⚠️ Duplicate URLs: {len(duplicate_urls)}")
print(f"⚠️ URLs with double ?v=: {len(bad_urls)}")

# === OPTIONAL: Print samples ===
if malformed_keys:
    print("\n🔍 Sample malformed keys:")
    for k in malformed_keys[:5]:
        print(f" - {k}")

if bad_urls:
    print("\n⚠️ Sample bad URLs:")
    for u in bad_urls[:5]:
        print(f" - {u}")

# === SAVE MAP ===
with open("cdn_map.json", "w", encoding="utf-8") as f:
    json.dump(cdn_map, f, indent=2, ensure_ascii=False)

print("\n📝 Saved cdn_map.json")