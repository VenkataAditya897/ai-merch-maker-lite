import os
import time
import base64
import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from io import BytesIO
from PIL import Image

load_dotenv()
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

def generate_text_from_gemini(text_prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Fallback mock response for demo if no key
        return (
            "Product Title: Galactic Cat Tee\n"
            "Product Description: A cosmic-themed t-shirt featuring a cute astronaut cat floating in space. Perfect for cat lovers and stargazers!\n"
            "Tags: cat, space, t-shirt, astronomy\n"
            "Price: 25.0\n"
            "Image Prompt: A photorealistic astronaut cat floating in a vibrant space background, perfect for printing on a t-shirt."
        )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=[types.Part(text=text_prompt)]
        )
        return response.candidates[0].content.parts[0].text
    except ClientError as e:
        return f"API Error: {e}"

def generate_image_from_cloudflare(prompt: str) -> str:
    """
    Generates an image using a free Stable Diffusion model on Cloudflare Workers AI.
    """
    if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ACCOUNT_ID:
        print("Error: Cloudflare API credentials missing in .env. Using fallback.")
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_assets", "sample_image.png"))

    try:
        # The API endpoint for the Stable Diffusion model
        api_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"
        
        headers = {
            "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json"
        }

        data = {
            "prompt": prompt,
            "negative_prompt": "blurry, ugly, bad quality, low-res"
        }

        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status()

        img_bytes = response.content
        
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_assets"))

        os.makedirs(output_dir, exist_ok=True)
        
        # Save the generated image locally
        image_path = os.path.join(output_dir, f"generated_image_{int(time.time())}.png")
        with open(image_path, "wb") as f:
            f.write(img_bytes)
            
        print(f"Generated image saved to: {image_path}")
        return image_path
    
    except Exception as e:
        print(f"Error generating image with Cloudflare AI: {e}")
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_assets", "sample_image.png"))