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
    seen_names = set()
    total_cards = 0  # Track total cards found

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
            print("   This will take several minutes for 1,410 products...")

            previous_product_count = 0
            scroll_attempts = 0
            max_scrolls = 100  # Increased for 1410 products
            no_new_products_count = 0

            while scroll_attempts < max_scrolls:
                # Scroll to bottom in multiple steps (more realistic)
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(0.5)

                # Wait for lazy loading
                time.sleep(2)

                # Check current product count
                current_product_count = len(page.query_selector_all("a.pdpurl"))

                # Progress update
                if current_product_count != previous_product_count:
                    print(f"  Scroll #{scroll_attempts + 1}: {current_product_count} product cards loaded")
                    no_new_products_count = 0

                    if progress_callback and current_product_count % 50 == 0:
                        progress_callback({
                            "count": current_product_count,
                            "done": False,
                            "message": f"Loading products... ({current_product_count} cards loaded)"
                        })
                else:
                    no_new_products_count += 1

                # Stop if no new products for 10 consecutive scrolls
                if no_new_products_count >= 10:
                    print(f"✅ No new products after {no_new_products_count} scrolls")
                    print(f"   Total product cards loaded: {current_product_count}")
                    break

                previous_product_count = current_product_count
                scroll_attempts += 1

                # Wait for network to settle occasionally
                if scroll_attempts % 5 == 0:
                    try:
                        page.wait_for_load_state("networkidle", timeout=3000)
                    except:
                        pass

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
                        continue

                    img_url = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy")
                    if not img_url:
                        continue

                    name = img.get_attribute("title") or img.get_attribute("alt") or card.text_content() or "Unnamed Product"
                    name = name.strip()

                    # Extract base product name (remove color variant after last comma)
                    # E.g., "Varsity Tommy Logo Crewneck Sweatshirt, Misty Plum" -> "Varsity Tommy Logo Crewneck Sweatshirt"
                    base_name = name
                    if ',' in name:
                        # Split on last comma to separate product name from color
                        parts = name.rsplit(',', 1)
                        base_name = parts[0].strip()

                    # Only add if we haven't seen this base product name before
                    if base_name and base_name not in seen_names:
                        seen_names.add(base_name)
                        products.append({
                            "name": name[:100],  # Keep full name with color for display
                            "base_name": base_name[:100],  # Store base name for reference
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

        print(f"✅ Final product count: {len(products)} unique products from {total_cards} cards")

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
