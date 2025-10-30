import os
import json
import time

base_dir = r"D:\csv\mediumresfacsimiles"
cdn_base = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/"
extensions = {".jpg", ".jpeg", ".png"}

# ⏱️ Use a consistent timestamp for all entries
version_token = int(time.time())

cdn_map = {}

for root, _, files in os.walk(base_dir):
    for file in files:
        if os.path.splitext(file)[1].lower() in extensions:
            rel_path = os.path.relpath(os.path.join(root, file), base_dir).replace("\\", "/")
            cdn_map[rel_path] = f"{cdn_base}{rel_path}?v={version_token}"

with open("cdn_map.json", "w", encoding="utf-8") as f:
    json.dump(cdn_map, f, indent=2)

print(f"Generated cdn_map.json with {len(cdn_map)} entries and cache-busting token v={version_token}.")