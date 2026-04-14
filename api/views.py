from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import ParleProduct as ParleProductModel
from .services.attribute_service import extract_attributes
from api.services.state_manager import get_initial_state, merge_state, is_complete
from api.services.speech_pipeline import localize_assistant_text, normalize_user_query
from api.services.decision_engine import (
    PRODUCT_NOT_FOUND_MESSAGE,
    WELCOME_MESSAGE,
    autofill_from_sku,
    enrich_state_from_product_text,
    get_next_question,
    get_question_image,
    get_question_products,
    has_product_matches,
    populate_state_from_product,
    resolve_product_from_state,
    should_show_variant_image,
)
# -----------------------------------
# FINAL RESPONSE BUILDER
# -----------------------------------
def build_final_response(state):
    return (
        "Your product has been added to cart. "
        "Please click Confirm to place the order, or add item to continue adding more products."
    )

def build_order_item(product, state):
    quantity = int(state["quantity"])
    weight = int(state["weight"])

    return {
        "sku_id": int(product.sku_id),
        "brand": product.brand,
        "mrp": product.mrp,
        "min_order": product.min_order,
        "box_amount": product.box_amount,
        "image_url": product.image_url,
        "imageurl": product.image_url,
        "quantity": quantity,
        "total_cost": product.mrp * quantity,
        "weight": weight,
    }


def merge_biscuit_items(existing_items, new_items):
    merged = list(existing_items or [])

    for item in new_items or []:
        sku_id = item.get("sku_id")
        existing_index = next(
            (index for index, existing_item in enumerate(merged) if existing_item.get("sku_id") == sku_id),
            None,
        )

        if existing_index is not None:
            merged[existing_index] = item
        else:
            merged.append(item)

    return merged


def build_response(reply, state, history, is_final=False, biscuit=None, imageurl=None, bs64audio=None, transcript=None):
    payload = {
        "reply": reply,
        "state": state,
        "history": history,
        "biscuit": biscuit or [],
        "order": is_final,
        "imageurl": imageurl,
        "bs64audio": bs64audio,
        "transcript": transcript,
    }

    if is_final:
        payload["answer"] = reply
        payload["nextquestion"] = None
    else:
        payload["answer"] = None
        payload["nextquestion"] = reply

    return Response(payload)


def build_recommendation_item(product, quantity=10):
    return {
        "sku_id": int(product.sku_id),
        "brand": product.brand,
        "variant": None,
        "mrp": product.mrp,
        "min_order": product.min_order,
        "box_amount": product.box_amount,
        "image_url": product.image_url,
        "imageurl": product.image_url,
        "quantity": quantity,
        "total_cost": product.mrp * quantity,
    }


def get_recommended_product(excluded_sku_ids):
    return (
        ParleProductModel.objects.exclude(sku_id__in=excluded_sku_ids)
        .order_by("sku_id")
        .first()
    )


# -----------------------------------
# MAIN VIEW
# -----------------------------------
class ParleProduct(APIView):
    def post(self, request):
        data = request.data

        source_language_code = (data.get("sourcelang") or "en").strip()
        audio_base64 = data.get("audiofile")
        should_generate_audio = bool(audio_base64)
        audio_mime_type = data.get("audioMimeType") or "audio/webm"
        normalized_input = normalize_user_query(
            user_query=(data.get("userQuery") or "").strip(),
            audio_base64=audio_base64,
            source_language_code=source_language_code,
            mime_type=audio_mime_type,
        )
        user_query = normalized_input["user_query_english"]
        transcript = normalized_input["user_query_original"]
        incoming_state = data.get("state")
        history = list(data.get("history") or []) 
        existing_biscuit = list(data.get("biscuit") or [])

        print(f"\nUser Query: {user_query}")

        state = get_initial_state(incoming_state)
        state = enrich_state_from_product_text(state)

        if not history and not user_query:
            history.append({"role": "assistant", "content": WELCOME_MESSAGE})
            localized_reply = localize_assistant_text(
                WELCOME_MESSAGE,
                source_language_code,
                generate_audio=should_generate_audio,
            )
            return build_response(
                localized_reply["text"],
                state,
                history,
                bs64audio=localized_reply["audio_base64"],
                transcript=transcript,
            )

        if user_query:
            history.append({"role": "user", "content": transcript or user_query})
            attributes = extract_attributes(user_query)
            print(f"\nExtracted Attributes: {attributes}")
            state = merge_state(state, attributes)
            state = enrich_state_from_product_text(state)
            print(f"\nMerged State: {state}")
        
        state, error = autofill_from_sku(state)

        if error:
            history.append({"role": "assistant", "content": error})
            localized_reply = localize_assistant_text(
                error,
                source_language_code,
                generate_audio=should_generate_audio,
            )
            return build_response(
                localized_reply["text"],
                state,
                history,
                bs64audio=localized_reply["audio_base64"],
                transcript=transcript,
            )

        if (state.get("product_name") or state.get("sku_id")) and not has_product_matches(state):
            history.append({"role": "assistant", "content": PRODUCT_NOT_FOUND_MESSAGE})
            localized_reply = localize_assistant_text(
                PRODUCT_NOT_FOUND_MESSAGE,
                source_language_code,
                generate_audio=should_generate_audio,
            )
            return build_response(
                localized_reply["text"],
                state,
                history,
                bs64audio=localized_reply["audio_base64"],
                transcript=transcript,
            )

        product = resolve_product_from_state(state)

        if state.get("variant"):
            state = populate_state_from_product(state, product)

        next_q = get_next_question(state)
        print(f"\nNext Question: {next_q}")
        show_variant_image = should_show_variant_image(state)
        question_products = [] if not is_complete(state) else get_question_products(state, product)
        question_image = get_question_image(state, product) if show_variant_image else None

        if next_q == "DONE" and is_complete(state):
            reply = build_final_response(state)
            is_final = True
            latest_item = [build_order_item(product, state)] if product else []
            final_biscuit = merge_biscuit_items(existing_biscuit, latest_item)
        else:
            reply = next_q
            is_final = False
            final_biscuit = []

        if not is_final:
            if show_variant_image:
                question_products = []
            else:
                question_products = []
                question_image = None

        localized_reply = localize_assistant_text(
            reply,
            source_language_code,
            generate_audio=should_generate_audio or is_final,
        )
        history.append({"role": "assistant", "content": localized_reply["text"]})

        return build_response(
            localized_reply["text"],
            state,
            history,
            is_final=is_final,
            biscuit=final_biscuit if is_final else question_products,
            imageurl=None if is_final else question_image,
            bs64audio=localized_reply["audio_base64"],
            transcript=transcript,
        )


class ConfirmOrderView(APIView):
    def post(self, request):
        biscuit = request.data.get("biscuit") or []
        excluded_sku_ids = [
            item.get("sku_id")
            for item in biscuit
            if item.get("sku_id") is not None
        ]

        recommended_product = get_recommended_product(excluded_sku_ids)
        frequently_ordered = []
        product_qty_message = ""

        if recommended_product:
            frequently_ordered = [build_recommendation_item(recommended_product, quantity=10)]
            product_qty_message = "Add 10 quantity of this product to this order?"

        return Response(
            {
                "answer": f"Thank you for placing your order with Parle. Your current order contains {len(biscuit)} product(s).",
                "frequently_ordered": frequently_ordered,
                "product_qty_message": product_qty_message,
                "current_ordered": biscuit,
            }
        )
