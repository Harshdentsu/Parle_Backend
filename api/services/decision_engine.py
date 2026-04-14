import re
from api.models import ParleProduct


WELCOME_MESSAGE = "Hi I am here to help you place orders for parle products, please provide product name or SKU ID?"
PRODUCT_NOT_FOUND_MESSAGE = "I could not find that product in the catalog. Please provide the correct product name or SKU ID."


def normalize_text(value):
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def infer_variant_from_brand(brand):
    brand_lower = (brand or "").lower()

    if "butter masala" in brand_lower:
        return "Butter Masala"
    if "creme" in brand_lower or "cream" in brand_lower:
        return "Creme"
    if "classic" in brand_lower:
        return "Classic"

    return None


def infer_product_name_from_brand(brand):
    brand_lower = (brand or "").lower()

    if "happy happy" in brand_lower:
        return "Happy Happy"
    if "krackjack" in brand_lower:
        return "Krackjack"
    if "monaco" in brand_lower:
        return "Monaco"
    if "black bourbon" in brand_lower or "bourbon" in brand_lower:
        return "Black Bourbon"
    if "parle marie" in brand_lower or "marie" in brand_lower:
        return "Parle Marie"
    if "parle-g" in brand_lower or "parle g" in brand_lower:
        return "Parle-G"

    return brand


def enrich_state_from_product_text(state):
    product_name = state.get("product_name")

    if product_name and not state.get("variant"):
        inferred_variant = infer_variant_from_brand(product_name)
        if inferred_variant:
            state["variant"] = inferred_variant
            state["product_name"] = infer_product_name_from_brand(product_name)

    return state

def matches_product(product, state):
    brand_norm = normalize_text(product.brand)
    product_name = state.get("product_name")
    variant = state.get("variant")

    if product_name:
        product_norm = normalize_text(product_name)
        if product_norm and product_norm not in brand_norm:
            return False

    if variant:
        variant_norm = normalize_text(variant)
        if variant_norm and variant_norm not in brand_norm:
            return False

    return True


def list_matching_products(state):
    if state.get("sku_id"):
        product = ParleProduct.objects.filter(sku_id=state["sku_id"]).first()
        return [product] if product else []

    matches = []
    for product in ParleProduct.objects.all():
        if matches_product(product, state):
            matches.append(product)

    return matches


def build_product_option(product):
    variant = infer_variant_from_brand(product.brand)
    return {
        "sku_id": int(product.sku_id),
        "brand": product.brand,
        "variant": variant,
        "mrp": product.mrp,
        "min_order": product.min_order,
        "box_amount": product.box_amount,
        "image_url": product.image_url,
        "imageurl": product.image_url,
        "quantity": 1,
        "total_cost": product.mrp,
    }


def get_variant_options(state):
    if state.get("sku_id") or not state.get("product_name") or state.get("variant"):
        return []

    options = []
    seen_variants = set()

    for product in list_matching_products(state):
        variant = infer_variant_from_brand(product.brand)
        if not variant or variant in seen_variants:
            continue
        seen_variants.add(variant)
        options.append(build_product_option(product))

    return options


def get_question_products(state, product=None):
    variant_options = get_variant_options(state)
    if variant_options:
        return variant_options

    if product:
        return [build_product_option(product)]

    return []


def should_show_variant_image(state):
    return bool(state.get("product_name")) and not state.get("variant") and len(get_variants(state["product_name"])) > 1


def get_question_image(state, product=None):
    if not should_show_variant_image(state):
        return None

    options = get_variant_options(state)
    if options:
        return options[0].get("imageurl") or options[0].get("image_url")

    if product:
        return product.image_url

    return None


def get_variants(product_name):
    product_name_lower = (product_name or "").lower().replace("-", " ")
    variants = set()

    for brand in ParleProduct.objects.values_list("brand", flat=True):
        brand_lower = brand.lower().replace("-", " ")
        if product_name_lower and product_name_lower not in brand_lower:
            continue

        variant = infer_variant_from_brand(brand)
        if variant:
            variants.add(variant)

    return sorted(variants)


def autofill_from_sku(state):
    if not state.get("sku_id"):
        return state, None

    product = ParleProduct.objects.filter(sku_id=state["sku_id"]).first()

    if not product:
        return state, "Invalid SKU ID, please check again."

    state["product_name"] = infer_product_name_from_brand(product.brand)
    state["variant"] = infer_variant_from_brand(product.brand)

    return state, None


def resolve_product_from_state(state):
    matches = list_matching_products(state)
    if len(matches) == 1:
        return matches[0]
    return None


def populate_state_from_product(state, product):
    if not product:
        return state

    if not state.get("sku_id"):
        state["sku_id"] = int(product.sku_id)

    if not state.get("product_name"):
        state["product_name"] = infer_product_name_from_brand(product.brand)

    if not state.get("variant"):
        state["variant"] = infer_variant_from_brand(product.brand)

    if not state.get("weight"):
        brand_lower = product.brand.lower()
        if "50" in brand_lower:
            state["weight"] = 50
        elif "100" in brand_lower:
            state["weight"] = 100

    return state


def has_product_matches(state):
    return len(list_matching_products(state)) > 0


def get_next_question(state):
    if not state.get("product_name") and not state.get("sku_id"):
        return WELCOME_MESSAGE

    if state.get("product_name") and not state.get("variant"):
        variants = get_variants(state["product_name"])

        if len(variants) > 1:
            return f"Which variant would you like for {state['product_name']}? Available options: {', '.join(variants)}."
        if len(variants) == 1:
            state["variant"] = variants[0]
        if len(variants) == 0:
            return PRODUCT_NOT_FOUND_MESSAGE

    if not state.get("weight"):
        return f"{state['product_name']} {state['variant']}, which weight do you need? 50 gms or 100 gms?"

    if not state.get("quantity"):
        return f"{state['product_name']} {state['variant']} {state['weight']} gms, how much quantity do you need?"

    return "DONE"
