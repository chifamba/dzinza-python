# backend/src/photo_utils.py

import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Placeholder image service URL
PLACEHOLDER_URL = "https://placehold.co/"

def generate_placeholder_image_url(width: int, height: int, text: str = "No Image",
                                   bg_color_hex: str = "cccccc", text_color_hex: str = "969696") -> str:
    """Generates a URL for a placeholder image using placehold.co."""
    # Basic validation
    width = max(10, int(width))
    height = max(10, int(height))
    text = text if text else "Placeholder"
    # Basic hex color validation (6 hex digits)
    bg_color_hex = bg_color_hex if len(bg_color_hex) == 6 and all(c in '0123456789abcdefABCDEF' for c in bg_color_hex) else "cccccc"
    text_color_hex = text_color_hex if len(text_color_hex) == 6 and all(c in '0123456789abcdefABCDEF' for c in text_color_hex) else "969696"

    # Construct the URL
    # Fixed F541: Added placeholders
    url = f"{PLACEHOLDER_URL}{width}x{height}/{bg_color_hex}/{text_color_hex}?text={requests.utils.quote(text)}"
    return url

def generate_initials_placeholder(first_name: str, last_name: str, size: int = 100) -> Image.Image:
    """Generates a simple placeholder image with initials."""
    initials = ""
    if first_name:
        initials += first_name[0].upper()
    if last_name:
        initials += last_name[0].upper()
    if not initials:
        initials = "?"

    # Removed unused variables: bg_color, text_color
    # Create an image with a light grey background
    image = Image.new('RGB', (size, size), color='#E0E0E0')
    draw = ImageDraw.Draw(image)

    # Use a default font (consider including a TTF font file for better results)
    try:
        # Adjust font size based on image size
        font_size = max(15, size // 3)
        # This relies on Pillow finding a default font. Might fail on minimal systems.
        font = ImageFont.truetype("arial.ttf", font_size) # Or specify path to a bundled font
    except IOError:
        # Fallback if default font isn't found
        font = ImageFont.load_default()
        print("Warning: Default font not found. Using fallback.")


    # Calculate text size and position
    # Use textbbox for potentially more accurate sizing with specific fonts
    try:
         # Pillow >= 9.2.0
         bbox = draw.textbbox((0, 0), initials, font=font)
         text_width = bbox[2] - bbox[0]
         text_height = bbox[3] - bbox[1]
    except AttributeError:
         # Fallback for older Pillow versions
         text_width, text_height = draw.textsize(initials, font=font)


    x = (size - text_width) / 2
    y = (size - text_height) / 2

    # Draw the text (dark grey)
    draw.text((x, y), initials, fill='#555555', font=font)

    return image

# Example usage (optional)
if __name__ == '__main__':
    # Example 1: Generate URL
    url = generate_placeholder_image_url(200, 150, text="John D.")
    print(f"Placeholder URL: {url}")

    # Example 2: Generate Initials Image and save it
    try:
        img = generate_initials_placeholder("Jane", "Smith", size=120)
        img.save("initials_placeholder.png")
        print("Saved initials_placeholder.png")
    except Exception as e:
        print(f"Could not generate or save initials placeholder: {e}")

