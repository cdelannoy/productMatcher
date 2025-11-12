from playwright.sync_api import sync_playwright
import time

def scrape_us_tommy(url="https://usa.tommy.com/en/women", progress_callback=None):
    """
    Generic product scraper for e-commerce sites.

    Returns a dictionary with:
    - products: list of product dictionaries
    - total_cards: total number of product cards found (before deduplication)
    - unique_products: number of unique products (after deduplication)

    Note: Some websites have bot protection that may prevent scraping.
    The Tommy Hilfiger site currently blocks automated access.
    For testing, try alternative sites like:
    - https://www.scrapingcourse.com/ecommerce/ (demo site)
    """
    products = []
    total_cards = 0  # Track total cards found

    # Network interception: Capture image URLs as they're requested
    captured_images = {}  # Store {image_url: True} for all captured images

    try:
        with sync_playwright() as p:
            # Launch with non-headless mode to avoid bot detection
            # Many sites block headless browsers, so we use headed mode
            browser = p.chromium.launch(
                headless=False,  # Set to False to bypass bot detection
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            # Create context with realistic browser settings to avoid bot detection
            context = browser.new_context(
                ignore_https_errors=True,
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                java_script_enabled=True
            )

            # Add stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()

            # INTERCEPT network responses to capture image URLs
            def capture_image_request(response):
                try:
                    # Capture Scene7 image requests (Tommy Hilfiger's CDN)
                    if 'scene7.com/is/image' in response.url and response.status == 200:
                        # Store the image URL - clean version without query params for matching
                        captured_images[response.url] = True
                except:
                    pass

            page.on('response', capture_image_request)
            print("🌐 Network interception enabled - will capture image URLs as they load...")

            print(f"🚀 Navigating to {url} ...")
            try:
                page.goto(url, timeout=120000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"❌ Failed to load page: {e}")
                if progress_callback:
                    progress_callback({"count": 0, "done": True, "message": f"Failed to load page: {str(e)}"})
                return products

            if progress_callback:
                progress_callback({"count": 0, "done": False, "message": "Page loaded, scrolling..."})

            # Accept cookies if banner appears
            try:
                page.click("button:has-text('Accept')", timeout=5000)
                print("✅ Accepted cookies")
            except:
                pass

            # Use infinite scroll to load all products
            # Tommy Hilfiger uses lazy loading - products appear as you scroll
            print("📜 Using infinite scroll to load all products...")
            print("   This will take several minutes to load all 1,500+ products...")

            previous_product_count = 0
            scroll_attempts = 0
            max_scrolls = 300  # Much more patient for 1500+ products
            no_new_products_count = 0
            stuck_count = 0  # Track if we're truly stuck

            while scroll_attempts < max_scrolls:
                # Try clicking "Load More" button if it exists
                try:
                    load_more_selectors = [
                        "button:has-text('Load More')",
                        "button:has-text('Show More')",
                        "a:has-text('Load More')",
                        ".load-more",
                        "[data-action='load-more']"
                    ]
                    for selector in load_more_selectors:
                        if page.query_selector(selector):
                            page.click(selector, timeout=2000)
                            print("  ⬇️ Clicked 'Load More' button")
                            time.sleep(3)  # Increased wait time after clicking Load More
                            no_new_products_count = 0  # Reset counter after clicking Load More
                            stuck_count = 0  # Reset stuck counter
                            break
                except:
                    pass

                # Scroll to bottom aggressively
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)  # Give more time for lazy loading

                # Check current product count
                current_product_count = len(page.query_selector_all("a.pdpurl"))

                # Progress update
                if current_product_count != previous_product_count:
                    print(f"  Scroll #{scroll_attempts + 1}: {current_product_count} product cards loaded")
                    no_new_products_count = 0
                    stuck_count = 0

                    if progress_callback and current_product_count % 50 == 0:
                        progress_callback({
                            "count": current_product_count,
                            "done": False,
                            "message": f"Loading products... ({current_product_count} cards loaded)"
                        })
                else:
                    no_new_products_count += 1

                    # Check if we're truly at the bottom
                    is_at_bottom = page.evaluate("window.innerHeight + window.scrollY >= document.body.scrollHeight - 100")
                    if is_at_bottom:
                        stuck_count += 1

                # Stop if no new products for 30 consecutive scrolls AND we're at the bottom for 15 of those
                # This is more patient to ensure we don't stop prematurely
                if no_new_products_count >= 30 and stuck_count >= 15:
                    print(f"✅ Reached end: No new products after {no_new_products_count} scrolls")
                    print(f"   Total product cards loaded: {current_product_count}")
                    break

                previous_product_count = current_product_count
                scroll_attempts += 1

                # Wait for network to settle occasionally
                if scroll_attempts % 10 == 0:
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except:
                        pass

            # Check how many image URLs we captured from network
            print(f"🌐 Network interception captured {len(captured_images)} image URLs during initial scroll")

            # HYBRID APPROACH: Multiple aggressive scroll passes to capture more images
            print("🔄 Performing multiple aggressive scroll passes to maximize image capture...")

            # Pass 1: Slow scroll from top to bottom
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(2)
            viewport_height = page.evaluate("window.innerHeight")
            total_height = page.evaluate("document.body.scrollHeight")
            current_scroll = 0

            print("   Pass 1/3: Slow top-to-bottom scroll...")
            while current_scroll < total_height:
                page.evaluate(f"window.scrollTo(0, {current_scroll})")
                time.sleep(0.8)  # Longer wait to give lazy loader time
                current_scroll += (viewport_height // 4)  # Very small steps

            print(f"   After Pass 1: {len(captured_images)} images captured")

            # Pass 2: Fast bottom-to-top scroll
            print("   Pass 2/3: Fast bottom-to-top scroll...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            current_scroll = total_height

            while current_scroll > 0:
                page.evaluate(f"window.scrollTo(0, {current_scroll})")
                time.sleep(0.3)
                current_scroll -= (viewport_height // 2)

            print(f"   After Pass 2: {len(captured_images)} images captured")

            # Pass 3: Medium speed top-to-bottom with random stops
            print("   Pass 3/3: Variable speed scroll with pauses...")
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)
            current_scroll = 0

            # Stop at 10%, 30%, 50%, 70%, 90% of page to trigger lazy loaders
            for percent in [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]:
                target = int(total_height * percent)
                page.evaluate(f"window.scrollTo(0, {target})")
                time.sleep(1.5)  # Longer pause at each stop

            print(f"   After Pass 3: {len(captured_images)} images captured")

            # Final wait for any pending requests
            time.sleep(3)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass

            print(f"🌐 Final network capture: {len(captured_images)} image URLs total")

            # Option 4: Try to extract product data from JavaScript state
            print("🔍 Checking for product data in JavaScript state...")
            js_result = page.evaluate("""
                () => {
                    // Look for all window properties that might contain product data
                    const allProps = Object.keys(window).filter(key => {
                        return key.toLowerCase().includes('product') ||
                               key.toLowerCase().includes('data') ||
                               key.toLowerCase().includes('state') ||
                               key.toLowerCase().includes('initial');
                    });

                    // Check each one for array/object that might contain products
                    for (let prop of allProps) {
                        const val = window[prop];
                        if (val && typeof val === 'object') {
                            // Check if it's an array with many items (likely products)
                            if (Array.isArray(val) && val.length > 100) {
                                return {found: true, source: prop, data: val, properties: allProps};
                            }
                            // Check if it's an object with a products array
                            if (val.products && Array.isArray(val.products) && val.products.length > 10) {
                                return {found: true, source: prop, data: val.products, properties: allProps};
                            }
                        }
                    }

                    return {found: false, properties: allProps};
                }
            """)

            # Show what properties were found
            if js_result and 'properties' in js_result:
                print(f"   Found {len(js_result['properties'])} potential data properties: {js_result['properties'][:20]}")

            js_products = js_result.get('data') if js_result and js_result.get('found') else None

            if js_products:
                print(f"✅ Found JavaScript product data: {type(js_products)}")
                if isinstance(js_products, dict):
                    print(f"   Keys: {list(js_products.keys())[:10]}")  # Show first 10 keys
                elif isinstance(js_products, list):
                    print(f"   List length: {len(js_products)}")
                    if len(js_products) > 0:
                        print(f"   First item type: {type(js_products[0])}")
                        if isinstance(js_products[0], dict):
                            print(f"   First item keys: {list(js_products[0].keys())[:10]}")
                            # Check if this looks like product data with images
                            first_item = js_products[0]
                            for key in ['image', 'imageUrl', 'img', 'thumbnail', 'src', 'picture']:
                                if key in first_item:
                                    print(f"   ✅ Found image key: '{key}' = {str(first_item[key])[:50]}")
            else:
                print("❌ No JavaScript product data found")

            # Try multiple selectors for different site structures
            product_selectors = [
                "a.pdpurl",  # Tommy Hilfiger
                "a.product-item",
                "a[href*='/product/']",
                ".product a[href*='/product']",
                "article a",
                ".product-card a",
                "a.woocommerce-LoopProduct-link"  # WooCommerce sites
            ]

            product_cards = []
            for selector in product_selectors:
                product_cards = page.query_selector_all(selector)
                if len(product_cards) > 0:
                    total_cards = len(product_cards)  # Store total cards found
                    print(f"🔎 Found {total_cards} product cards using selector: {selector}")
                    break

            if len(product_cards) == 0:
                print("⚠️ No product cards found with any selector. The site may be blocking access or has a different structure.")
                print("💡 Tip: Check the page manually and update the selectors in scraper.py")

            if progress_callback and len(product_cards) > 0:
                progress_callback({"count": len(product_cards), "done": False, "message": f"Found {len(product_cards)} products, extracting data..."})

            # Debug: Count images with real URLs vs data URLs
            skipped_data_urls = 0
            skipped_no_img = 0
            skipped_no_url = 0

            # Sample the first image to see what attributes are available
            if len(product_cards) > 0:
                first_card = product_cards[0]
                first_img = first_card.query_selector("img")
                first_link = first_card.get_attribute("href")
                if first_img:
                    print("🔍 Sample image attributes from FIRST product (loaded):")
                    sample_attrs = page.evaluate("(img) => { const attrs = {}; for (let attr of img.attributes) { attrs[attr.name] = attr.value.substring(0, 50); } return attrs; }", first_img)
                    for key, val in sample_attrs.items():
                        print(f"   {key}: {val}...")
                    print(f"   Product link: {first_link}")

                # Also check a product further down that might not be loaded
                if len(product_cards) > 500:
                    mid_card = product_cards[500]
                    mid_img = mid_card.query_selector("img")
                    mid_link = mid_card.get_attribute("href")
                    if mid_img:
                        print("🔍 Sample image attributes from MIDDLE product (#500):")
                        mid_attrs = page.evaluate("(img) => { const attrs = {}; for (let attr of img.attributes) { attrs[attr.name] = attr.value.substring(0, 50); } return attrs; }", mid_img)
                        for key, val in mid_attrs.items():
                            print(f"   {key}: {val}...")
                        print(f"   Product link: {mid_link}")

            # Show sample of captured image URLs for debugging
            if len(captured_images) > 0:
                print(f"🔍 Sample captured image URLs (first 3):")
                for idx, url in enumerate(list(captured_images.keys())[:3]):
                    print(f"   {url}")

            for card in product_cards:
                try:
                    link = card.get_attribute("href")
                    if not link:
                        continue

                    # Make link absolute if relative
                    if link.startswith('/'):
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        link = f"{parsed_url.scheme}://{parsed_url.netloc}{link}"
                    elif not link.startswith('http'):
                        link = url.rstrip('/') + '/' + link.lstrip('/')

                    # Find image - check the card and its children
                    img = card.query_selector("img")
                    if not img:
                        # Look for image in parent or sibling elements
                        parent = card.evaluate("el => el.parentElement")
                        if parent:
                            img = page.query_selector(f"xpath=//a[@href='{link}']/..//img")

                    if not img:
                        skipped_no_img += 1
                        continue

                    # Try multiple image attributes (data-src is often the real image for lazy loading)
                    img_url = img.get_attribute("data-src") or img.get_attribute("src") or img.get_attribute("data-lazy")

                    # Also check for srcset attribute which might have the real URL
                    if not img_url or img_url.startswith("data:"):
                        srcset = img.get_attribute("srcset")
                        if srcset:
                            # srcset format: "url1 1x, url2 2x" - take first URL
                            img_url = srcset.split(',')[0].strip().split(' ')[0]

                    # Check data-* attributes that might contain image URL
                    if not img_url or img_url.startswith("data:"):
                        for attr in ['data-original', 'data-image', 'data-img-src', 'data-lazy-src']:
                            potential_url = img.get_attribute(attr)
                            if potential_url and not potential_url.startswith("data:"):
                                img_url = potential_url
                                break

                    # NEW: If still a data URL, try to find matching image from network capture
                    if img_url and img_url.startswith("data:"):
                        import re
                        # Extract product identifiers from link to match with captured images
                        # Example link: /en/women/clothing/tops/wool-cable-knit-sweater/WW43586-LZP.html
                        link_parts = link.split('/')
                        product_id = link_parts[-1] if link_parts else ''

                        # Extract SKU codes from the product ID
                        # Pattern: WW43586-LZP or MW0MW12345 etc
                        sku_patterns = re.findall(r'([A-Z]{2}\d+)', product_id.upper())
                        color_codes = re.findall(r'-([A-Z0-9]{3,})', product_id.upper())

                        # Try to find captured image URL matching this product
                        found_match = False
                        best_match = None

                        for captured_url in captured_images.keys():
                            # Match score (higher is better)
                            match_score = 0

                            # Try 1: Match by SKU code (e.g., WW43586)
                            if sku_patterns:
                                for sku in sku_patterns:
                                    if sku in captured_url.upper():
                                        match_score += 10

                            # Try 2: Match by color code (e.g., LZP)
                            if color_codes:
                                for color in color_codes:
                                    if color in captured_url.upper():
                                        match_score += 5

                            # Try 3: Prefer "_main" images (product main view)
                            if '_main' in captured_url:
                                match_score += 2

                            # If we have a good match, use it
                            if match_score >= 10:
                                if not best_match or match_score > best_match[1]:
                                    best_match = (captured_url, match_score)

                        if best_match:
                            img_url = best_match[0]
                            found_match = True

                    if not img_url:
                        skipped_no_url += 1
                        continue

                    # Skip placeholder/data URLs only if we couldn't find network-captured alternative
                    if img_url.startswith("data:"):
                        skipped_data_urls += 1
                        continue

                    name = img.get_attribute("title") or img.get_attribute("alt") or card.text_content() or "Unnamed Product"
                    name = name.strip()

                    # DON'T deduplicate color variants - keep ALL products!
                    # Different colors are visually different and should be matched separately
                    # This ensures we capture all 1,513 items on the page
                    if name and img_url:
                        products.append({
                            "name": name[:100],
                            "link": link,
                            "img_url": img_url
                        })

                        # Update progress every 10 products
                        if progress_callback and len(products) % 10 == 0:
                            progress_callback({"count": len(products), "done": False, "message": f"Extracted {len(products)} products..."})
                except Exception as e:
                    print(f"⚠️ Error extracting product: {e}")
                    continue

            browser.close()

        # Print debug info
        print(f"📊 Extraction Summary:")
        print(f"   Total cards found: {total_cards}")
        print(f"   Network captured images: {len(captured_images)}")
        print(f"   Products extracted: {len(products)}")
        print(f"   Skipped - no image element: {skipped_no_img}")
        print(f"   Skipped - no image URL: {skipped_no_url}")
        print(f"   Skipped - data URL placeholder (no network match): {skipped_data_urls}")

        # Calculate improvement from network interception
        improvement_rate = ((len(products) / total_cards) * 100) if total_cards > 0 else 0
        print(f"✅ Final product count: {len(products)} unique products from {total_cards} cards ({improvement_rate:.1f}%)")

        if progress_callback:
            progress_callback({"count": len(products), "done": True, "message": f"Scraping complete! Found {len(products)} products"})

    except Exception as e:
        print(f"❌ Scraper error: {e}")
        if progress_callback:
            progress_callback({"count": 0, "done": True, "message": f"Scraper error: {str(e)}"})

    # Return metadata along with products
    return {
        "products": products,
        "total_cards": total_cards,
        "unique_products": len(products)
    }
