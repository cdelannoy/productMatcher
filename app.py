from flask import Flask, request, jsonify, render_template_string, render_template, Response
from PIL import Image
import requests
from io import BytesIO
import torch
import clip
import time
import threading
import json
from playwright.sync_api import sync_playwright
from scraper import scrape_us_tommy

# ---------------------------
# Setup CLIP
# ---------------------------
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def get_embedding(image):
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        embedding = model.encode_image(image_input)
    return embedding / embedding.norm(dim=-1, keepdim=True)

# ---------------------------
# Flask App
# ---------------------------
app = Flask(__name__)
progress_data = {"count": 0, "done": False}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/progress_stream")
def progress_stream():
    def event_stream():
        last_count = -1
        while True:
            time.sleep(1)
            if progress_data["count"] != last_count:
                last_count = progress_data["count"]
                yield f"data: {json.dumps(progress_data)}\n\n"
            if progress_data.get("done"):
                break
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/search", methods=["POST"])
def search():
    if "image" not in request.files:
        return jsonify([])

    ad_file = request.files["image"]
    top_x = int(request.form.get("top_x", 5))
    target_url = request.form.get("target_url", "https://usa.tommy.com/en/women")

    # Open uploaded ad image
    ad_img = Image.open(ad_file).convert("RGB")
    ad_emb = get_embedding(ad_img)

    print(f"Scraping products from {target_url} ...")
    products = scrape_us_tommy(target_url)

    results = []
    for p in products:
        try:
            resp = requests.get(p["img_url"], timeout=10)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            emb = get_embedding(img)
            score = torch.cosine_similarity(ad_emb, emb).item()
            results.append({"product": p, "score": score})
        except Exception as e:
            print("⚠️ Error processing product:", e)
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(results[:top_x])


if __name__ == "__main__":
    app.run(debug=True)
