import boto3
import csv
import json
import re
import time
import unicodedata
from botocore.config import Config

# Configuration
ACCESS_KEY_ID = '2ae153703e0bfa298058a5916b148f02'
SECRET_ACCESS_KEY = '6c89032c195dac0047a7c83287d3f08083738b7861d800e1005d448458a56eea'
ACCOUNT_ID = '3a166d1f20174deac8fb4ae74b35c1a0'
BUCKET_NAME = 'mediumresfacsimiles'
BASE_URL = 'https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/'  # Updated to public dev URL
CSV_PATH = 'mural_master_regenerated.csv'
JSON_PATH = 'cdn_map.json'
DEFAULT_PAGE_W = 10.79  # Default from samples
DEFAULT_PAGE_H = 18.0   # Adjust as needed
TIMESTAMP = int(time.time())

# Slugify function from your code
def slugify(text):
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text.lower().strip("_")

# Create S3 client for R2
s3 = boto3.client(
    's3',
    endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=SECRET_ACCESS_KEY,
    config=Config(signature_version='s3v4')
)

# Function to list all objects recursively and group by folder (prefix)
def get_folders_and_files():
    folders = {}
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=''):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.jpg') and 'Page_' in key:
                # Get folder (prefix up to last /)
                folder = key.rsplit('/', 1)[0]
                if folder not in folders:
                    folders[folder] = []
                folders[folder].append(key)
    return folders

# Main update function
def update_files():
    folders = get_folders_and_files()
    cdn_map = {}
    csv_data = []
    existing_handles = {}

    # Read existing CSV if exists
    try:
        with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                handle = row['Handle']
                existing_handles[handle] = row
    except FileNotFoundError:
        pass

    for folder, files in folders.items():
        if not files:
            continue
        
        # Sort files to ensure correct order
        files.sort(key=lambda k: k.split('/')[-1])
        
        # Count pages - assume all .jpg are pages
        pages = len(files)
        
        # Derive title from folder
        title = re.sub(r'\(\d+\)$', f'({pages} pages)', folder) if re.search(r'\(\d+\)$', folder) else f"{folder} ({pages} pages)"
        
        # Generate handle
        title_base = re.sub(r'\(\d+\)$', '', folder).strip()
        handle = slugify(title_base) + f"_{pages}"
        
        # Get or set page dimensions, title, etc. - use existing if handle matches
        existing = existing_handles.get(handle, {})
        page_w = existing.get('Page Width (cm)', DEFAULT_PAGE_W)
        page_h = existing.get('Page Height (cm)', DEFAULT_PAGE_H)
        csv_title = existing.get('Title', title)  # Prefer existing title if available
        
        # Add to CSV data
        csv_data.append({
            'Handle': handle,
            'Title': csv_title,
            'Pages': pages,
            'Page Width (cm)': page_w,
            'Page Height (cm)': page_h
        })
        
        # Add to cdn_map
        for file_key in files:
            url = f"{BASE_URL}{file_key}?v={TIMESTAMP}"
            cdn_map[file_key] = url

    # Write updated CSV (overwrite with merged data)
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Handle', 'Title', 'Pages', 'Page Width (cm)', 'Page Height (cm)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Write updated JSON
    with open(JSON_PATH, 'w', encoding='utf-8') as jsonfile:
        json.dump(cdn_map, jsonfile, indent=4)

    print(f"Updated CSV with {len(csv_data)} entries and JSON with {len(cdn_map)} mappings.")

# Run the update
if __name__ == "__main__":
    update_files()