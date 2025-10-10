from playwright.sync_api import sync_playwright
from flask import Flask, request, jsonify, render_template_string, Response
import json, time

import time
import threading
from playwright.sync_api import sync_playwright

# Shared dict for progress info
progress_data = {"count": 0, "done": False, "products": []}
progress_lock = threading.Lock()

def scrape_us_tommy(url="https://usa.tommy.com/en/women"):
    products = []
    seen_names = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print(f"🚀 Navigating to {url} ...")
        page.goto(url, timeout=120000, wait_until="domcontentloaded")

        # Accept cookies if banner appears
        try:
            page.click("button:has-text('Accept')", timeout=5000)
            print("✅ Accepted cookies")
        except:
            pass

        # Infinite scroll for lazy-loaded products
        previous_height = None
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(5)
            current_height = page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                break
            previous_height = current_height

        # Grab all product anchors
        product_cards = page.query_selector_all("a.pdpurl")
        print(f"🔎 Found {len(product_cards)} product cards")

        for card in product_cards:
            try:
                link = card.get_attribute("href")
                if link and not link.startswith("http"):
                    link = "https://usa.tommy.com" + link

                img = card.query_selector("img")
                if not img:
                    continue

                img_url = img.get_attribute("src") or img.get_attribute("data-src")
                name = img.get_attribute("title") or img.get_attribute("alt") or "Unnamed Product"

                if name not in seen_names:
                    seen_names.add(name)
                    products.append({
                        "name": name.strip(),
                        "link": link,
                        "img_url": img_url
                    })
            except Exception as e:
                print("⚠️ Error extracting product:", e)

        browser.close()

    print(f"✅ Final product count: {len(products)}")
    return products
