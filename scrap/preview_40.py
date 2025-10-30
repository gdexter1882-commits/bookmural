import os
from PIL import Image
import matplotlib.pyplot as plt

# Path to the original image
IMAGE_PATH = r"D:\csv\mediumresfacsimiles\crane_stephen_the_red_badge_of_courage_1898_facsimile_235\page_004.jpg"

# Load original
original = Image.open(IMAGE_PATH).convert("RGB")
w, h = original.size

# Resize to 40%
scaled = original.resize((int(w * 0.4), int(h * 0.4)), Image.LANCZOS)

# Show side-by-side
fig, axs = plt.subplots(1, 2, figsize=(12, 6))
axs[0].imshow(original)
axs[0].set_title(f"Original ({w}×{h})")
axs[0].axis("off")

axs[1].imshow(scaled)
axs[1].set_title(f"Scaled 40% ({scaled.size[0]}×{scaled.size[1]})")
axs[1].axis("off")

plt.tight_layout()
plt.show()