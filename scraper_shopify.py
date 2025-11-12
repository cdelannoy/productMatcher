"""
Shopify JSON API Scraper - Works with ANY Shopify store!
No API key needed. No browser automation. Just clean REST API calls.

Perfect for demos - real products from real stores.
Works with: Boulder Gear, Allbirds, Gymshark, Fashion Nova, and thousands more Shopify stores.
"""

import requests
import time


def scrape_shopify_collection(store_url, collection="womens", max_products=50, progress_callback=None):
    """
    Fetch products from any Shopify store using their public JSON API.

    Args:
        store_url: Store domain (e.g., "bouldergear.com", "allbirds.com")
        collection: Collection handle (e.g., "womens", "mens", "new-arrivals")
                   Use "all" for all products
        max_products: Maximum number of products to fetch (default: 50)
        progress_callback: Optional callback for progress updates

    Returns:
        Dictionary with products, total_cards, and unique_products
    """
    products = []

    try:
        # Normalize store URL
        store_url = store_url.replace("https://", "").replace("http://", "").split("/")[0]

        print(f"🚀 Fetching products from Shopify store: {store_url}")
        print(f"   Collection: {collection}")
        print(f"   Max products: {max_products}")

        if progress_callback:
            progress_callback({
                "count": 0,
                "done": False,
                "message": f"Connecting to {store_url}..."
            })

        # Shopify JSON API endpoint
        if collection == "all":
            url = f"https://{store_url}/products.json"
        else:
            url = f"https://{store_url}/collections/{collection}/products.json"

        # Add limit parameter (max 250 per Shopify)
        params = {"limit": min(max_products, 250)}

        print(f"📡 Making API request to: {url}")
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        shopify_products = data.get('products', [])

        print(f"✅ API Response received!")
        print(f"   Found {len(shopify_products)} products")

        if progress_callback:
            progress_callback({
                "count": len(shopify_products),
                "done": False,
                "message": f"Processing {len(shopify_products)} products..."
            })

        # Process products
        for idx, item in enumerate(shopify_products):
            try:
                # Extract product info
                title = item.get('title', 'Unnamed Product')
                handle = item.get('handle', '')
                product_url = f"https://{store_url}/products/{handle}"

                # Get first variant for price
                variants = item.get('variants', [])
                price = None
                if variants:
                    price = variants[0].get('price')

                # Get first image
                images = item.get('images', [])
                img_url = None
                if images:
                    img_url = images[0].get('src')

                # Skip if no image
                if not img_url:
                    continue

                products.append({
                    "name": title[:100],
                    "link": product_url,
                    "img_url": img_url,
                    "price": f"${price}" if price else None
                })

                # Progress update every 5 products
                if progress_callback and (idx + 1) % 5 == 0:
                    progress_callback({
                        "count": len(products),
                        "done": False,
                        "message": f"Processed {len(products)} products..."
                    })

            except Exception as e:
                print(f"⚠️ Error processing product: {e}")
                continue

        print(f"\n📊 Shopify API Fetch Summary:")
        print(f"   Products fetched: {len(products)}")
        print(f"✅ Success!")

        if progress_callback:
            progress_callback({
                "count": len(products),
                "done": True,
                "message": f"Complete! Fetched {len(products)} products from {store_url}"
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


# Convenience functions for Boulder Gear
def scrape_bouldergear_womens(progress_callback=None):
    """Scrape Boulder Gear women's collection"""
    return scrape_shopify_collection(
        store_url="bouldergear.com",
        collection="womens",
        max_products=50,
        progress_callback=progress_callback
    )


def scrape_bouldergear_mens(progress_callback=None):
    """Scrape Boulder Gear men's collection"""
    return scrape_shopify_collection(
        store_url="bouldergear.com",
        collection="mens",
        max_products=50,
        progress_callback=progress_callback
    )


def scrape_bouldergear_all(progress_callback=None):
    """Scrape all Boulder Gear products"""
    return scrape_shopify_collection(
        store_url="bouldergear.com",
        collection="all",
        max_products=100,
        progress_callback=progress_callback
    )


# Generic wrapper for any Shopify store
def scrape_shopify_url(url, progress_callback=None):
    """
    Smart wrapper that extracts store domain and collection from URL.

    Examples:
        - "bouldergear.com" → womens collection
        - "https://bouldergear.com/collections/mens" → mens collection
        - "allbirds.com/collections/womens-shoes" → womens-shoes collection
    """
    # Parse URL
    url = url.replace("https://", "").replace("http://", "")
    parts = url.split("/")

    store_url = parts[0]
    collection = "womens"  # default

    # Extract collection from URL if present
    if "collections" in parts:
        collection_idx = parts.index("collections")
        if len(parts) > collection_idx + 1:
            collection = parts[collection_idx + 1]

    print(f"🔍 Detected Shopify store: {store_url}")
    print(f"   Collection: {collection}")

    return scrape_shopify_collection(
        store_url=store_url,
        collection=collection,
        max_products=50,
        progress_callback=progress_callback
    )


if __name__ == "__main__":
    # Test the API
    print("🧪 Testing Boulder Gear (Shopify) scraper...\n")

    def test_progress(data):
        print(f"   Progress: {data.get('message', '')}")

    result = scrape_bouldergear_womens(progress_callback=test_progress)

    print(f"\n{'='*60}")
    print(f"TEST RESULTS:")
    print(f"{'='*60}")
    print(f"Products fetched: {len(result['products'])}")

    if result['products']:
        print(f"\n🔍 Sample products (first 3):")
        for i, p in enumerate(result['products'][:3], 1):
            print(f"\n  {i}. {p['name'][:60]}")
            print(f"     Price: {p['price']}")
            print(f"     Link: {p['link'][:70]}...")
            print(f"     Image: {p['img_url'][:70]}...")

    print(f"\n{'='*60}")
    print("✅ Boulder Gear (Shopify) scraper test complete!")
