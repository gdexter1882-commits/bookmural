import json
import time

# === CONFIGURATION ===
R2_PUBLIC_BASE = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev"
VERSION_TOKEN = int(time.time())

# === LOAD UNSLUGIFIED KEYS ===
with open("unslugified_keys.log", "r", encoding="utf-8") as f:
    keys = [line.strip() for line in f if line.strip()]

# === BUILD CDN MAP ===
cdn_map = {}
for key in keys:
    url = f"{R2_PUBLIC_BASE}/{key}?v={VERSION_TOKEN}"
    cdn_map[key] = url

print(f"✅ Built CDN map with {len(cdn_map)} unslugified entries")

# === SAVE TO FILE ===
with open("cdn_map.json", "w", encoding="utf-8") as f:
    json.dump(cdn_map, f, indent=2, ensure_ascii=False)

print("📝 Saved cdn_map.json with cache-busting suffix")