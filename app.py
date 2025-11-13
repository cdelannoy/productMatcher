from flask import Flask, request, jsonify, render_template_string, render_template, Response
from PIL import Image
import requests
from io import BytesIO
import torch
import clip
import time
import threading
import json
import ssl
from playwright.sync_api import sync_playwright
from scraper import scrape_us_tommy
from scraper_shopify import scrape_shopify_url, scrape_bouldergear_womens
from improved_matcher import (
    get_multi_scale_embeddings,
    compute_advanced_similarity,
    rerank_with_diversity
)

# ---------------------------
# Setup CLIP
# ---------------------------
# Handle SSL certificate issues for CLIP model download
ssl._create_default_https_context = ssl._create_unverified_context

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading CLIP model on device: {device}")
model, preprocess = clip.load("ViT-B/32", device=device)
print("✅ CLIP model loaded successfully")

def get_embedding(image):
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
    return embedding / embedding.norm(dim=-1, keepdim=True)

# ---------------------------
# Flask App
# ---------------------------
app = Flask(__name__)
progress_data = {"count": 0, "done": False, "message": ""}
progress_lock = threading.Lock()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/progress_stream")
def progress_stream():
    def event_stream():
        last_count = -1
        while True:
            time.sleep(0.5)
            with progress_lock:
                current_data = progress_data.copy()

            if current_data["count"] != last_count or current_data.get("message"):
                last_count = current_data["count"]
                yield f"data: {json.dumps(current_data)}\n\n"

            if current_data.get("done"):
                break
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/search", methods=["POST"])
def search():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        ad_file = request.files["image"]
        top_x = int(request.form.get("top_x", 5))
        target_url = request.form.get("target_url", "bouldergear.com")
        deduplicate = request.form.get("deduplicate") == "on"  # Checkbox value

        # Reset progress
        with progress_lock:
            progress_data["count"] = 0
            progress_data["done"] = False
            progress_data["message"] = "Starting scrape..."

        # Open uploaded ad image and get multi-scale embeddings
        try:
            ad_img = Image.open(ad_file).convert("RGB")
            print("🔍 Extracting multi-scale embeddings from query image...")
            ad_embeddings = get_multi_scale_embeddings(ad_img, model, preprocess, device)
        except Exception as e:
            return jsonify({"error": f"Failed to process image: {str(e)}"}), 400

        # Progress callback function
        def update_progress(data):
            with progress_lock:
                progress_data.update(data)

        print(f"Scraping products from {target_url} ...")

        # Route to appropriate scraper
        if "bouldergear.com" in target_url:
            scraper_result = scrape_bouldergear_womens(progress_callback=update_progress)
        elif ".myshopify.com" in target_url or any(domain in target_url for domain in ["allbirds", "gymshark", "fashionnova"]):
            scraper_result = scrape_shopify_url(target_url, progress_callback=update_progress)
        elif "tommy.com" in target_url:
            scraper_result = scrape_us_tommy(target_url, progress_callback=update_progress)
        else:
            # Default to Boulder Gear for unknown URLs
            scraper_result = scrape_bouldergear_womens(progress_callback=update_progress)

        # Extract products and metadata from scraper result
        products = scraper_result.get("products", [])
        total_cards = scraper_result.get("total_cards", 0)
        unique_products = scraper_result.get("unique_products", len(products))

        if not products:
            with progress_lock:
                progress_data["done"] = True
                progress_data["message"] = "No products found on the page"
            return jsonify({"results": [], "total_products_searched": 0, "total_cards_loaded": 0, "matches_returned": 0})

        # Update progress for matching phase
        with progress_lock:
            progress_data["message"] = "Matching products with your image..."
            progress_data["done"] = False

        results = []
        total_products = len(products)
        print(f"🎯 Using advanced matching algorithm with {len(products)} products...")

        for idx, p in enumerate(products):
            try:
                resp = requests.get(p["img_url"], timeout=10)
                img = Image.open(BytesIO(resp.content)).convert("RGB")

                # Get multi-scale embeddings for product
                product_embeddings = get_multi_scale_embeddings(img, model, preprocess, device)

                # Compute advanced similarity score
                score = compute_advanced_similarity(ad_embeddings, product_embeddings)

                results.append({"product": p, "score": score})

                # Update progress every 5 products during matching
                if (idx + 1) % 5 == 0:
                    with progress_lock:
                        progress_data["message"] = f"Matching images... {idx + 1}/{total_products}"
            except Exception as e:
                print(f"⚠️ Error processing product {p.get('name', 'unknown')}: {e}")
                continue

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        # Apply diversity re-ranking if requested
        if deduplicate:
            print(f"🔄 Re-ranking top results for diversity...")
            results_top = rerank_with_diversity(results, top_k=top_x, diversity_weight=0.2)
        else:
            print(f"📋 Returning top {top_x} results without deduplication...")
            results_top = results[:top_x]

        # Mark as done
        with progress_lock:
            progress_data["done"] = True
            progress_data["message"] = f"Complete! Found top {len(results_top)} matches"

        # Return results with metadata
        return jsonify({
            "results": results_top,
            "total_products_searched": total_products,
            "total_cards_loaded": total_cards,
            "matches_returned": len(results_top)
        })

    except Exception as e:
        print(f"❌ Error in search endpoint: {e}")
        with progress_lock:
            progress_data["done"] = True
            progress_data["message"] = f"Error: {str(e)}"
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
