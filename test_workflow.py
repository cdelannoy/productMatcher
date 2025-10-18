#!/usr/bin/env python3
"""
Quick test script to verify the complete workflow
"""
from PIL import Image
import torch
import clip
import ssl

# Setup SSL
ssl._create_default_https_context = ssl._create_unverified_context

# Load CLIP
device = "cpu"
print("Loading CLIP model...")
model, preprocess = clip.load("ViT-B/32", device=device)
print("✅ CLIP model loaded")

def get_embedding(image):
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
    return embedding / embedding.norm(dim=-1, keepdim=True)

# Test with the screenshot
test_image_path = "files/Screenshot 2025-10-16 at 2.14.46 PM.png"
print(f"\nLoading test image: {test_image_path}")
img = Image.open(test_image_path).convert("RGB")
print(f"Image size: {img.size}")

# Get embedding
print("Getting image embedding...")
emb = get_embedding(img)
print(f"✅ Embedding shape: {emb.shape}")

# Test scraper
print("\nTesting scraper...")
from scraper import scrape_us_tommy

products = scrape_us_tommy("https://usa.tommy.com/en/women")
print(f"✅ Found {len(products)} products")

if len(products) > 0:
    print(f"\nFirst 3 products:")
    for i, p in enumerate(products[:3]):
        print(f"  {i+1}. {p['name']}")

print("\n✅ All components working! Ready to run the Flask app.")
print("Run: python app.py")
