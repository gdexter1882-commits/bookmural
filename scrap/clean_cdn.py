import json
import re

# Load the original cdn_map.json
with open("cdn_map.json", "r", encoding="utf-8") as f:
    cdn_map = json.load(f)

# ✅ Audit-style filtering: must contain 'page_' and end with '.jpg'
malformed_keys = []
cleaned_map = {}

for key, url in cdn_map.items():
    normalized_key = key.replace("\\", "/")
    if "page_" in normalized_key and normalized_key.lower().endswith(".jpg"):
        cleaned_map[key] = url
    else:
        malformed_keys.append(key)

print(f"✅ Retained {len(cleaned_map)} valid entries out of {len(cdn_map)}")
print(f"🧹 Removed {len(malformed_keys)} malformed entries")

# Save cleaned version
with open("cdn_map.cleaned.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_map, f, indent=2, ensure_ascii=False)

# Log malformed keys
with open("malformed_keys.log", "w", encoding="utf-8") as f:
    for key in malformed_keys:
        f.write(key + "\n")

print("📄 Saved cleaned map as cdn_map.cleaned.json")
print("🪵 Logged malformed keys to malformed_keys.log")