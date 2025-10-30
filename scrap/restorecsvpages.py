import csv
from collections import defaultdict
import re

# Input files
ORIGINAL_CSV = 'mural_master.csv'
REGENERATED_CSV = 'mural_master_regenerated.csv'
OUTPUT_CSV = 'mural_master_regenerated.csv'  # Set to overwrite the regenerated file directly

def normalize_title(title):
    # Remove page count suffix like "(77 pages)" and strip
    title = re.sub(r'\s*\(\d+ pages\)$', '', title).strip()
    return title.lower()

def map_dimensions():
    # Step 1: Read dimensions from original CSV into a dict keyed by normalized Title
    dimensions = defaultdict(dict)
    with open(ORIGINAL_CSV, newline='', encoding='utf-8') as orig_file:
        reader = csv.DictReader(orig_file)
        for row in reader:
            title = row.get('Title', '').strip()
            norm_title = normalize_title(title)
            if norm_title:
                dimensions[norm_title] = {
                    'Page Width (cm)': row.get('Page Width (cm)', ''),
                    'Page Height (cm)': row.get('Page Height (cm)', '')
                }
    
    # Step 2: Read regenerated CSV, update dimensions where normalized titles match, and collect rows
    updated_rows = []
    with open(REGENERATED_CSV, newline='', encoding='utf-8') as regen_file:
        reader = csv.DictReader(regen_file)
        fieldnames = reader.fieldnames  # Preserve original columns
        for row in reader:
            title = row.get('Title', '').strip()
            norm_title = normalize_title(title)
            if norm_title in dimensions:
                row['Page Width (cm)'] = dimensions[norm_title]['Page Width (cm)']
                row['Page Height (cm)'] = dimensions[norm_title]['Page Height (cm)']
            updated_rows.append(row)
    
    # Step 3: Write updated rows back to the regenerated CSV (overwriting it)
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
    
    print(f"Overwrote {OUTPUT_CSV} with {len(updated_rows)} rows, updating dimensions from {ORIGINAL_CSV} based on normalized titles.")

if __name__ == "__main__":
    map_dimensions()