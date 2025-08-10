import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

API_BASE = f"https://{SHOPIFY_STORE}/admin/api/2023-07"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ACCESS_TOKEN,
}
import base64

def publish_to_shopify(product_json):
    if not SHOPIFY_STORE or not ACCESS_TOKEN:
        return {"status": "error", "message": "Shopify credentials not set"}

    try:
        # Prepare product data for Shopify API
        product_data = {
            "product": {
                "title": product_json.get("title"),
                "body_html": product_json.get("description"),
                "tags": ", ".join(product_json.get("tags", [])),
                "variants": [{
                    "price": str(product_json.get("price", "0.00"))
                }],
                "metafields": [
                    {
                        "namespace": "ai_data",
                        "key": "caption",
                        "value": product_json.get("caption", ""),
                        "type": "single_line_text_field"
                    }
                ]
            }
        }

        # Step 1: Create product (without image)
        url = f"{API_BASE}/products.json"
        response = requests.post(url, json=product_data, headers=HEADERS)
        response.raise_for_status()
        product_resp = response.json()
        product_id = product_resp["product"]["id"]

        orig_image_path = product_json.get("image_path_abs")
        mockup_image_path = product_json.get("mockup_path_abs")

        for image_path in [mockup_image_path, orig_image_path]:
            if image_path and os.path.isfile(image_path):
                with open(image_path, "rb") as f:
                    encoded_string = base64.b64encode(f.read()).decode('utf-8')
                    image_payload = {"image": {"attachment": encoded_string}}
                    img_url = f"{API_BASE}/products/{product_id}/images.json"
                    img_resp = requests.post(img_url, json=image_payload, headers=HEADERS)
                    img_resp.raise_for_status()

        return {"status": "success", "shopify_product_id": product_id}

    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {e.response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
