# -----------------------------------
# DEFAULT STATE
# -----------------------------------
DEFAULT_STATE = {
    "product_name": None,
    "variant": None,
    "weight": None,
    "quantity": None,
    "sku_id": None
}


# -----------------------------------
# NORMALIZE STATE
# -----------------------------------
def normalize_state(state):
    normalized = DEFAULT_STATE.copy()
    normalized.update(state or {})
    return normalized


# -----------------------------------
# INIT STATE
# -----------------------------------
def get_initial_state(incoming_state=None):
    if not incoming_state:
        return DEFAULT_STATE.copy()

    return normalize_state(incoming_state)


# -----------------------------------
# MERGE STATE
# -----------------------------------
def merge_state(old_state, new_data):
    updated = old_state.copy()

    # SKU priority
    if new_data.get("sku_id"):
        updated["sku_id"] = new_data["sku_id"]
        updated["product_name"] = None
        updated["variant"] = None
        updated["weight"] = None

    for key in updated:
        if new_data.get(key) is not None:
            updated[key] = new_data[key]

    return updated


# -----------------------------------
# CHECK COMPLETE
# -----------------------------------
def is_complete(state):
    return (
        (state.get("product_name") or state.get("sku_id")) and
        state.get("variant") and
        state.get("weight") and
        state.get("quantity")
    )