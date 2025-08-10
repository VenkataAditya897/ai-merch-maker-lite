from fastapi import FastAPI
from pydantic import BaseModel
import json
import os

from ai_client import generate_text_from_gemini, generate_image_from_cloudflare

app = FastAPI()

class ProductOutput(BaseModel):
    title: str
    description: str
    tags: list[str]
    price: float
    product_type: str
    image_path: str

@app.get("/")
def root():
    return {"message": "AI Merch Maker Generator API"}

@app.post("/generate", response_model=ProductOutput)
def generate_product():
    llm_prompt = """
    You are generating a product listing for a merchandise item to be sold on a Shopify store.

    Please provide ONLY the following fields, each on its own line, in this exact format:

    Product Title: <a short, catchy product title, 3-5 words, and always end with the product type, e.g., 'Cute Cat T-shirt'>
    Product Description: <a 50-70 word description focused on the product’s features, style, and appeal — do NOT mention AI or how it was made>
    Tags: <a comma-separated list of relevant search tags, e.g. 't-shirt, cat, space'>
    Price: <a realistic retail price in dollars, between 10 and 50, with 1 decimal place>
    Product Type: <must be one of these three only — t-shirt, cup, or cap. Choose a random one each time.>
    Image Prompt: <a detailed and vivid description of the image/design to be printed on the product - like the graphic on a T-shirt or mug>

    The product must be a tangible item a t-shirt, cup, or cap, and the image prompt should describe how the product looks visually.

    Do NOT include any other text, explanation, or formatting.
    """

    raw_text = generate_text_from_gemini(llm_prompt)

    title, description, tags, image_prompt = "", "", [], ""
    product_type = ""
    price = 0.0

    # Try to parse the raw_text more flexibly
    for line in raw_text.split("\n"):
        line_lower = line.lower().strip()
        if "product title" in line_lower:
            try:
                title = line.split(":", 1)[1].strip()
            except IndexError:
                pass
        elif "product description" in line_lower:
            try:
                description = line.split(":", 1)[1].strip()
            except IndexError:
                pass
        elif "tags" in line_lower:
            try:
                tags = [tag.strip() for tag in line.split(":", 1)[1].split(",")]
            except IndexError:
                pass
        elif "price" in line_lower:
            try:
                price_str = line.split(":", 1)[1].strip()
                price = float(price_str)
            except (IndexError, ValueError):
                price = 0.0
        elif "product type" in line_lower:
            try:
                product_type = line.split(":", 1)[1].strip().lower()
            except IndexError:
                product_type = ""
        elif "image prompt" in line_lower or "image generation prompt" in line_lower:
            try:
                image_prompt = line.split(":", 1)[1].strip()
            except IndexError:
                pass

    # Fallback if no image prompt detected
    if not image_prompt:
        image_prompt = f"An artistic image for the product titled '{title}'"

    # Ensure tags is a list, even if empty
    if not tags:
        tags = []

    image_path = generate_image_from_cloudflare(image_prompt)

    # Save JSON output for demo
    os.makedirs("output", exist_ok=True)
    output_json = {
        "title": title,
        "description": description,
        "tags": tags,
        "price": price,
        "product_type": product_type,
        "image_path": image_path
    }
    with open("output/product.json", "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2)

    return output_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8001)
