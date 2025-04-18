# backend/src/photo_utils.py
import hashlib

def generate_default_person_photo(person_id: str, size: int = 150) -> str:
    """
    Generates a placeholder image URL based on the person's ID.
    Uses placehold.co for generating simple placeholder images.

    Args:
        person_id (str): The unique ID of the person.
        size (int): The desired size (width and height) of the placeholder image.

    Returns:
        str: A URL to a placeholder image.
    """
    if not person_id:
        # Default placeholder if ID is missing
        return f"https://localhost:8080/assets/profiles/images/default.png"

    # Use a hash of the person_id to generate somewhat consistent colors
    # This is a simple way to get varied placeholders without external libraries
    try:
        hash_obj = hashlib.md5(person_id.encode('utf-8')).hexdigest()
        # Use parts of the hash for background/text colors (simple example)
        bg_color = hash_obj[:6]
        text_color = hash_obj[6:12]
        # Extract first initial (or first two letters) for the placeholder text
        initials = person_id[:2].upper() # Use first 2 chars of ID as placeholder text
    except Exception:
        # Fallback if hashing fails
        bg_color = "EFEFEF"
        text_color = "AAAAAA"
        initials = "?"

    # Construct the placehold.co URL
    # Example: https://placehold.co/150x150/abcdef/123456?text=AB
    placeholder_url = f"https://localhost:8080/assets/profiles/images/?text={initials}"

    return placeholder_url

# Example usage (optional)
if __name__ == '__main__':
    test_id_1 = "82f28529-6b5d-4c30-a2d7-a18349c12564"
    test_id_2 = "2a7b5741-4e34-468d-85da-ec3343718d37"
    print(f"Photo URL for {test_id_1[:8]}...: {generate_default_person_photo(test_id_1)}")
    print(f"Photo URL for {test_id_2[:8]}...: {generate_default_person_photo(test_id_2)}")
    print(f"Photo URL for empty ID: {generate_default_person_photo('')}")
