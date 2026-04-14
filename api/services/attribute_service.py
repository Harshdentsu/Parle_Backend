
from api.utils.preprocessing import preprocess_query
from .llm_service import extract_attributes_llm

# -----------------------------------
# DEFAULT ATTRIBUTE STRUCTURE
# -----------------------------------
DEFAULT_ATTRIBUTES = {
    "product_name": None,
    "variant": None,
    "weight": None,
    "quantity": None,
    "sku_id": None
}

# -----------------------------------
# MERGE LOGIC
# -----------------------------------
def merge_attributes(hints, llm_output):
    final = {}

    for key in DEFAULT_ATTRIBUTES:

        if key == "quantity":
            final[key] = llm_output.get(key) or hints.get(key)

        elif key == "product_name":
            final[key] = hints.get(key) or llm_output.get(key)

        else:
            final[key] = hints.get(key) or llm_output.get(key)

    return final

# -----------------------------------
# CHECK IF LLM IS NEEDED
# -----------------------------------
def should_call_llm(hints):
    # If nothing extracted → call LLM
    if all(value is None for value in hints.values()):
        return True

    # If product info missing → call LLM
    if not hints.get("product_name") and not hints.get("sku_id"):
        return True

    return False

# -----------------------------------
# MAIN FUNCTION
# -----------------------------------
def extract_attributes(user_query: str):
    """
    Returns final extracted attributes
    """

    # Step 1: Preprocess
    processed = preprocess_query(user_query)
    cleaned_query = processed["cleaned_query"]
    hints = processed["hints"]
    print("Cleaned Query:", cleaned_query)
    print("\nPreprocessing Hints:", hints)

    # Step 2: Decide LLM usage
    use_llm = should_call_llm(hints)

    llm_output = DEFAULT_ATTRIBUTES.copy()

    # Step 3: Call LLM if needed
    if use_llm:
        try:
            llm_output = extract_attributes_llm(cleaned_query)
            print("\nLLM Output:", llm_output)
        except Exception as e:
            print("LLM failed:", e)

    # Step 4: Merge
    final_attributes = merge_attributes(hints, llm_output)

    return final_attributes