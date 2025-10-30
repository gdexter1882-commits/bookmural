import os
import csv
import re
import unicodedata

ORIGINAL_CSV = r"D:\csv\mural_master.csv"
IMAGE_ROOT = r"D:\csv\mediumresfacsimiles"
OUTPUT_CSV = r"D:\csv\mural_master_regenerated.csv"

def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.lower().strip("-")

# Build slug → full folder path map
folder_map = {}
for dirpath, dirnames, _ in os.walk(IMAGE_ROOT):
    for dirname in dirnames:
        folder_slug = slugify(dirname)
        folder_map[folder_slug] = os.path.join(dirpath, dirname)

with open(ORIGINAL_CSV, newline='', encoding='utf-8') as infile, \
     open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as outfile:

    reader = csv.DictReader(infile)
    writer = csv.writer(outfile)
    writer.writerow(["Handle", "Title", "Pages", "Page Width (cm)", "Page Height (cm)"])

    unmatched = 0
    matched = 0

    for row in reader:
        original_handle = row.get("Handle", "").strip()
        handle_slug = slugify(original_handle)

        matched_folder = None
        for folder_slug, folder_path in folder_map.items():
            if folder_slug in handle_slug or handle_slug in folder_slug:
                matched_folder = os.path.basename(folder_path)
                break

        if matched_folder:
            writer.writerow([
                matched_folder,
                row.get("Title", "").strip(),
                row.get("Pages", "").strip(),
                row.get("Page Width (cm)", "").strip(),
                row.get("Page Height (cm)", "").strip()
            ])
            matched += 1
        else:
            unmatched += 1
            print(f"❌ No folder match for: {original_handle}")

print(f"\n✅ Regenerated mural_master.csv with {matched} matched entries")
print(f"⚠️ Skipped {unmatched} unmatched entries")