import re

# -------------------------------
# BASIC CLEANING
# -------------------------------
def clean_text(text: str) -> str:
    if not text:
        return ""
    return text.strip().lower()


def remove_noise(text: str) -> str:
    noise_words = [
        "please", "i want", "can you", "give me",
        "suggest", "show me", "tell me", "i need",
        "would like", "buy", "get me"
    ]

    for word in noise_words:
        text = re.sub(r'\b' + word + r'\b', '', text)

    return text.strip()


# -------------------------------
# NORMALIZATION FUNCTIONS
# -------------------------------

# Extract ALL numbers first
def extract_numbers(text: str):
    return [int(x) for x in re.findall(r'\d+', text)]


#  Weight extraction (context-based)
def normalize_weight(text: str):
    match = re.search(r'(\d+)\s*(gm|g|grams)\b', text)
    if match:
        weight = int(match.group(1))
        if weight in [50, 100]:
            return weight
    return None


# Quantity extraction (strict context)
def normalize_quantity(text: str):
    match = re.search(r'(\d+)\s*(packs|packets|units|pieces|pcs)\b', text)
    if match:
        return int(match.group(1))
    return None


#  SKU extraction
def extract_sku(text: str):
    match = re.search(r'\b\d{6,8}\b', text)
    if match:
        return int(match.group())
    return None


#  Product normalization (improved)
def normalize_product(text: str):
    mapping = {
        "parle g": "Parle-G Classic",
        "parleg": "Parle-G Classic",
        "krackjack": "Krackjack",
        "krack jack": "Krackjack",
        "crack jack": "Krackjack",
        "monaco": "Monaco",
        "bourbon": "Black Bourbon",
        "black bourbon": "Black Bourbon",
        "happy happy": "Happy Happy",
        "marie": "Parle Marie Classic"
    }

    for key, value in mapping.items():
        if key in text:
            return value

    return None


# Variant normalization
def normalize_variant(text: str):
    if "classic" in text:
        return "Classic"

    if "cream" in text or "creme" in text:
        return "Creme"

    if "butter" in text:
        return "Butter Masala"

    return None


# -------------------------------
# SMART FALLBACK NUMBER LOGIC
# -------------------------------
def infer_missing_values(text, weight, quantity):
    numbers = extract_numbers(text)

    # Treat standalone 50/100 as weight when the user replies with just the size.
    if weight is None and len(numbers) == 1 and numbers[0] in [50, 100]:
        weight = numbers[0]

    # Remove already used weight
    if weight and weight in numbers:
        numbers.remove(weight)

    # If quantity missing → take remaining number
    if not quantity and numbers:
        quantity = numbers[-1]  # usually last number is quantity

    return weight, quantity


# -------------------------------
# MAIN PREPROCESS FUNCTION
# -------------------------------
def preprocess_query(user_query: str):
    text = clean_text(user_query)
    text = remove_noise(text)

    # Step 1: Extract directly
    weight = normalize_weight(text)
    quantity = normalize_quantity(text)

    # Step 2: Smart fallback (handles mixed inputs)
    weight, quantity = infer_missing_values(text, weight, quantity)

    hints = {
        "product_name": normalize_product(text),
        "variant": normalize_variant(text),
        "weight": weight,
        "quantity": quantity,
        "sku_id": extract_sku(text)
    }

    return {
        "cleaned_query": text,
        "hints": hints
    }
