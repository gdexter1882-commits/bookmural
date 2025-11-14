import csv
import unicodedata
import re
import os 
import math

# --- Configuration (Set the R2 Base URL for Covers) ---
R2_COVERS_BASE_URL = "https://pub-391c14324a544917a28a9e0955bfc219.r2.dev/covers"

# --- Utility Functions ---

def slugify(text):
# ... existing code ...
    return text.lower().strip("_")

# --- MOVED THIS FUNCTION to be top-level ---
def get_folder_key_from_title(title_str: str) -> str:
    """
    Extracts the R2 folder key from the full title.
    Example: "Voltaire, Candide, 1759 facsimile (194 pages)"
    Returns: "Voltaire, Candide, 1759 facsimile (194)"
    """
    # This regex finds the last occurrence of (XXX pages) and captures the part before it
    # and the number inside.
    match = re.match(r'^(.*?)\s*\((\d+)\s*pages\s*\)$', title_str.strip())
    if match:
        base_name = match.group(1).strip()
        page_count = match.group(2)
        # Reconstructs the folder key format
        return f"{base_name} ({page_count})"
    
    # Fallback if no " (XXX pages)" suffix is found
    # This logic may need to be adjusted if titles vary
    print(f"⚠️ Could not parse folder key from title: '{title_str}'", flush=True)
    return title_str.strip()
# --- END OF MOVE ---

def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
# ... existing code ...
    return best_layout

def get_eligible_texts(wall_w, wall_h, csv_path, cdn_map):
    """
    Finds all texts that fit the given wall dimensions.
    """
    eligible = []
    
    # --- THIS HELPER FUNCTION is now defined at the top level ---
    # def get_folder_key_from_title(title_str: str) -> str:
    #     ...
    # --- END OF MOVED BLOCK ---

    try:
        with open(csv_path, mode='r', encoding='utf-8') as file:
# ... existing code ...
# ... existing code ...
                        # --- Folder Key ---
                        folder_key = get_folder_key_from_title(title)

                        # --- Cover URL ---
# ... existing code ...
# ... existing code ...
    return eligible