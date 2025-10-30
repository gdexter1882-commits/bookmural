import json
import re

with open("cdn_map.json", "r", encoding="utf-8") as f:
    cdn_map = json.load(f)

valid_pattern = re.compile(r"/page_\d{3}\.jpg$", re.IGNORECASE)

malformed = []
for key in cdn_map:
    normalized = key.replace("\\", "/")
    if not valid_pattern.search(normalized):
        malformed.append(normalized)

print(f"⚠️ Found {len(malformed)} malformed keys")
print("\n🔍 Sample malformed keys:")
for k in malformed[:20]:
    print(f" - {k}")