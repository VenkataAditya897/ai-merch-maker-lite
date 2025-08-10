import requests
import json
import os
import time
from state import StateDB
from shopify_client import publish_to_shopify
from requests.exceptions import HTTPError, ConnectionError, Timeout


from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
from io import BytesIO



GENERATOR_URL = "http://localhost:8001/generate"  
MOCKUP_URL = "http://localhost:3000/mockup"
PUBLISHER_URL = "http://localhost:8000/api.php"

def print_api_error(response):
    try:
        err_json = response.json()
        # You can adjust this based on your API's error response structure
        error_message = err_json.get('error', {}).get('message') or str(err_json)
        print(f"API error response: {error_message}")
    except Exception:
        print(f"API returned HTTP {response.status_code} {response.reason} but no JSON error message.")
# Load model once globally 
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

def generate_image_caption(image_path_or_url: str) -> str:
    try:
        if image_path_or_url.startswith("http"):
            response = requests.get(image_path_or_url)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        else:
            image = Image.open(image_path_or_url).convert('RGB')
    except Exception as e:
        print(f"Error loading image for captioning: {e}")
        return ""

    inputs = processor(image, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)
    return caption


def main(run_once=True):
    db = StateDB()

    print("Starting orchestrator run...")

    # Step 1: Call generator
    print("Requesting product generation...")
    try:
        r = requests.post(GENERATOR_URL)
        r.raise_for_status()
        product = r.json()
    except ConnectionError:
        print("Error generating product: Could not connect to the generation service. Is the server running?")
        return
    except HTTPError as e:
        if e.response.status_code == 401:
            print("Error generating product: Unauthorized. Check your API token or credentials.")
        elif e.response.status_code == 429:
            print("Error generating product: Rate limit exceeded. Try again later.")
        else:
            print(f"HTTP error during product generation: {e.response.status_code} - {e.response.reason}")
        return
    except Timeout:
        print("Error generating product: Request timed out. Try again later.")
        return
    except Exception as e:
        print(f"Unexpected error generating product: {e}")
        return

    title = product.get("title")
    if db.is_published(title):
        print(f"Product '{title}' already published. Skipping.")
        return

    print(f"Generated product: {title}")

    # Step 2: Call mockup API
    print("Calling mockup API...")
    pt = product.get("product_type", "").lower().replace("-", "")
    # Build correct absolute path relative to orchestrator dir
    image_path = product.get("image_path", "")
    orchestrator_dir = os.path.dirname(os.path.abspath(__file__))
    abs_path = os.path.abspath(os.path.join(orchestrator_dir, "..", "demo_assets", os.path.basename(image_path)))

    mockup_payload = {
        "image_url": abs_path,
        "product_type": pt,
        "color": "white"
    }

    try:
        r = requests.post(MOCKUP_URL, json=mockup_payload)
        r.raise_for_status()
        mockup_response = r.json()
    except HTTPError as e:
        print(f"HTTP error during mockup: {e}")
        if e.response is not None:
            print_api_error(e.response)
        return
    except ConnectionError:
        print("Error during mockup: Could not connect to the mockup server. Is it running?")
        return
    except Timeout:
        print("Error during mockup: Request timed out.")
        return
    except Exception as e:
        print(f"Error during mockup: {e}")
        return

    mockup_url = mockup_response.get("mockup_url", "N/A")

    mockup_filename = os.path.basename(mockup_url)
    mockup_path_abs = os.path.abspath(os.path.join(orchestrator_dir, "..", "mockup", "output", mockup_filename))

    print("Generating caption for mockup image...")
    caption = generate_image_caption(mockup_path_abs)
    print(f"Generated caption: {caption}")

    # Step 3: Call fake publisher
    print("Publishing product...")
    publish_payload = product.copy()
    publish_payload["mockup_url"] = mockup_path_abs
    publish_payload["caption"] = caption
    try:
        r = requests.post(PUBLISHER_URL, json=publish_payload)
        r.raise_for_status()
        publish_response = r.json()

    except ConnectionError:
        print("Error publishing product: Could not connect to the fake publisher server. Is it running?")
        return
    except HTTPError as e:
        print(f"HTTP error publishing product: {e}")
        if e.response is not None:
            print_api_error(e.response)
        return
    except Timeout:
        print("Error publishing product: Request timed out.")
        return
    except Exception as e:
        print(f"Unexpected error publishing product: {e}")
        return

    fake_id = publish_response.get("fake_product_id", "N/A")
    print(f"Product published with fake ID: {fake_id}")

    # Step 4: Save state
    db.save_record(title, fake_id, mockup_path_abs, caption=caption, tags=product.get("tags", []))

    print("Record saved to state DB.")

    # Step 5: Shopify publish (stub)
    # Prepare local paths for Shopify images
    product["image_path_abs"] = abs_path
    product["mockup_path_abs"] = mockup_path_abs   

    print("Preparing to publish to Shopify...")
    try:
        shopify_resp = publish_to_shopify(product)
        print(f"Shopify publish response: {shopify_resp}")
    except Exception as e:
        print(f"Error publishing to Shopify: {e}")
        return
    

    print("Orchestrator run complete.")

if __name__ == "__main__":
    main()
