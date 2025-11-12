"""
Fake Store API Scraper - Free, Fast, Reliable!
No API key needed. No browser automation. Just clean REST API calls.

Perfect for demos - real clothing products with images.
API Docs: https://fakestoreapi.com/
"""

import requests
import time


def scrape_fakestore_api(category="women's clothing", progress_callback=None):
    """
    Fetch products from Fake Store API.

    Args:
        category: Product category
                  - "women's clothing" (default)
                  - "men's clothing"
                  - "jewelery"
                  - "electronics"
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary with products, total_cards, and unique_products
    """
    products = []

    try:
        print(f"🚀 Fetching products from Fake Store API...")
        print(f"   Category: {category}")

        if progress_callback:
            progress_callback({
                "count": 0,
                "done": False,
                "message": "Connecting to Fake Store API..."
            })

        # Fake Store API endpoint - super simple!
        url = f"https://fakestoreapi.com/products/category/{category}"

        print(f"📡 Making API request to: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        print(f"✅ API Response received!")
        print(f"   Found {len(data)} products")

        if progress_callback:
            progress_callback({
                "count": len(data),
                "done": False,
                "message": f"Processing {len(data)} products..."
            })

        # Process products
        for idx, item in enumerate(data):
            try:
                # Extract product info
                name = item.get('title', 'Unnamed Product')
                img_url = item.get('image')
                price = item.get('price')
                description = item.get('description', '')[:200]  # Truncate description

                # Note: Fake Store API doesn't provide direct product links
                # We'll create a fake product ID link for demo purposes
                product_id = item.get('id')
                link = f"https://fakestoreapi.com/products/{product_id}"

                # Skip if no image
                if not img_url:
                    continue

                products.append({
                    "name": name[:100],
                    "link": link,
                    "img_url": img_url,
                    "price": f"${price}" if price else None
                })

                # Progress update
                if progress_callback and (idx + 1) % 5 == 0:
                    progress_callback({
                        "count": len(products),
                        "done": False,
                        "message": f"Processed {len(products)} products..."
                    })

            except Exception as e:
                print(f"⚠️ Error processing product: {e}")
                continue

        print(f"\n📊 API Fetch Summary:")
        print(f"   Products fetched: {len(products)}")
        print(f"✅ Success!")

        if progress_callback:
            progress_callback({
                "count": len(products),
                "done": True,
                "message": f"Complete! Fetched {len(products)} products from Fake Store API"
            })

        return {
            "products": products,
            "total_cards": len(products),
            "unique_products": len(products)
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"API Error: {str(e)}"
        print(f"❌ {error_msg}")

        if progress_callback:
            progress_callback({"count": 0, "done": True, "message": error_msg})

        return {"products": [], "total_cards": 0, "unique_products": 0}

    except Exception as e:
        print(f"❌ Error: {e}")

        if progress_callback:
            progress_callback({"count": 0, "done": True, "message": f"Error: {str(e)}"})

        return {"products": [], "total_cards": 0, "unique_products": 0}


# Convenience functions for common categories
def scrape_fakestore_womens(progress_callback=None):
    """Scrape Fake Store women's clothing"""
    return scrape_fakestore_api(
        category="women's clothing",
        progress_callback=progress_callback
    )


def scrape_fakestore_mens(progress_callback=None):
    """Scrape Fake Store men's clothing"""
    return scrape_fakestore_api(
        category="men's clothing",
        progress_callback=progress_callback
    )


def scrape_fakestore_all_clothing(progress_callback=None):
    """Scrape both men's and women's clothing from Fake Store"""
    products = []

    print("🚀 Fetching all clothing products...")

    # Get women's clothing
    womens = scrape_fakestore_api("women's clothing", progress_callback=progress_callback)
    products.extend(womens.get("products", []))

    # Get men's clothing
    mens = scrape_fakestore_api("men's clothing", progress_callback=progress_callback)
    products.extend(mens.get("products", []))

    print(f"✅ Total clothing products: {len(products)}")

    return {
        "products": products,
        "total_cards": len(products),
        "unique_products": len(products)
    }


if __name__ == "__main__":
    # Test the API
    print("🧪 Testing Fake Store API scraper...\n")

    def test_progress(data):
        print(f"   Progress: {data.get('message', '')}")

    result = scrape_fakestore_womens(progress_callback=test_progress)

    print(f"\n{'='*60}")
    print(f"TEST RESULTS:")
    print(f"{'='*60}")
    print(f"Products fetched: {len(result['products'])}")

    if result['products']:
        print(f"\n🔍 Sample products (first 3):")
        for i, p in enumerate(result['products'][:3], 1):
            print(f"\n  {i}. {p['name'][:60]}")
            print(f"     Price: {p['price']}")
            print(f"     Link: {p['link']}")
            print(f"     Image: {p['img_url'][:70]}...")

    print(f"\n{'='*60}")
    print("✅ Fake Store API scraper test complete!")
