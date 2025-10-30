import json
from collections import Counter

# Load the CDN map
with open("cdn_map.json", "r", encoding="utf-8") as f:
    cdn_map = json.load(f)

keys = list(cdn_map.keys())
urls = list(cdn_map.values())

# Check for duplicate keys
key_counts = Counter(keys)
duplicate_keys = [k for k, v in key_counts.items() if v > 1]

# Check for duplicate URLs
url_counts = Counter(urls)
duplicate_urls = [u for u, v in url_counts.items() if v > 1]

# Check for malformed keys
bad_keys = [k for k in keys if not k.lower().endswith(".jpg") or "page_" not in k]

# Check for double ?v= in URLs
bad_urls = [u for u in urls if u.count("?v=") > 1]

# Summary
print(f"🔍 Total entries: {len(cdn_map)}")
print(f"⚠️ Duplicate keys: {len(duplicate_keys)}")
print(f"⚠️ Duplicate URLs: {len(duplicate_urls)}")
print(f"⚠️ Malformed keys: {len(bad_keys)}")
print(f"⚠️ URLs with double ?v=: {len(bad_urls)}")

# Optional: print samples
if duplicate_keys:
    print("\n🔁 Sample duplicate keys:")
    for k in duplicate_keys[:5]:
        print(f" - {k}")

if bad_urls:
    print("\n⚠️ Sample bad URLs:")
    for u in bad_urls[:5]:
        print(f" - {u}")