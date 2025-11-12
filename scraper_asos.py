from playwright.sync_api import sync_playwright
import time
import json
import re

def scrape_asos(url="https://www.asos.com/us/women/new-in/new-in-clothing/cat/?cid=27108", progress_callback=None):
    """
    Scraper for ASOS e-commerce site.
    ASOS has much better structure than Tommy Hilfiger - products are in the page source!

    Returns a dictionary with:
    - products: list of product dictionaries
    - total_cards: total number of product cards found
    - unique_products: number of unique products
    """
    products = []
    total_cards = 0

    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=False,  # Can often use headless=True with ASOS
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )

            # Add stealth
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()

            print(f"🚀 Navigating to ASOS: {url}")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"❌ Failed to load page: {e}")
                if progress_callback:
                    progress_callback({"count": 0, "done": True, "message": f"Failed to load page: {str(e)}"})
                return {"products": products, "total_cards": 0, "unique_products": 0}

            if progress_callback:
                progress_callback({"count": 0, "done": False, "message": "Page loaded, scrolling..."})

            # Accept cookies
            try:
                page.click("#onetrust-accept-btn-handler", timeout=5000)
                print("✅ Accepted cookies")
            except:
                pass

            # Wait for products to load initially
            print("⏳ Waiting for products to load...")
            time.sleep(5)

            # Scroll to load more products - ASOS lazy loads in batches
            print("📜 Scrolling to load all products (this may take a while for large catalogs)...")
            previous_product_count = 0
            scroll_attempts = 0
            max_scrolls = 200  # Increased for large catalogs (3,539 products)
            no_new_products_count = 0

            while scroll_attempts < max_scrolls:
                # Scroll to bottom
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)  # Increased from 1.5 to 2 seconds for better loading

                # Check product count using the /prd/ link selector
                current_count = len(page.query_selector_all("a[href*='/prd/']"))

                if current_count != previous_product_count:
                    print(f"  Scroll #{scroll_attempts + 1}: {current_count} products loaded (+{current_count - previous_product_count})")
                    no_new_products_count = 0

                    if progress_callback and current_count % 50 == 0:
                        progress_callback({
                            "count": current_count,
                            "done": False,
                            "message": f"Loading products... ({current_count} loaded)"
                        })
                else:
                    no_new_products_count += 1

                # Stop if no new products for 8 consecutive scrolls (increased patience)
                if no_new_products_count >= 8:
                    print(f"✅ Reached end after {scroll_attempts + 1} scrolls - no new products loaded")
                    print(f"   Total products loaded: {current_count}")
                    break

                previous_product_count = current_count
                scroll_attempts += 1

                # Every 20 scrolls, wait a bit longer for network
                if scroll_attempts % 20 == 0:
                    print(f"   🔄 Checkpoint: {current_count} products loaded so far...")
                    time.sleep(3)  # Longer pause at checkpoints

            # Extract products from ASOS's data structure
            print("🔍 Extracting product data...")

            # Method 1: Try to find product data in page source (ASOS often embeds JSON)
            page_content = page.content()

            # Look for JSON data in script tags
            script_data = page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    for (let script of scripts) {
                        const content = script.textContent;
                        // Look for product data patterns
                        if (content.includes('"products"') || content.includes('"items"')) {
                            try {
                                // Try to extract JSON
                                const jsonMatch = content.match(/window\\.asos\\.pdp\\.config\\.product\\s*=\\s*({.+?});/s);
                                if (jsonMatch) {
                                    return {found: true, type: 'pdp', data: jsonMatch[1]};
                                }

                                // Look for other patterns
                                const storeMatch = content.match(/"searchTerm".+?"products":\\s*\\[(.+?)\\]/s);
                                if (storeMatch) {
                                    return {found: true, type: 'search', data: storeMatch[0]};
                                }
                            } catch (e) {
                                // Continue searching
                            }
                        }
                    }
                    return {found: false};
                }
            """)

            if script_data and script_data.get('found'):
                print(f"✅ Found embedded product data (type: {script_data.get('type')})")

            # Method 2: Extract product data directly from <li> containers
            # ASOS structure: <li class="productTile_..."><a><img></a></li>
            # Find all <li> elements that contain product links
            product_containers = page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/prd/"]'));
                    const containers = new Set();

                    links.forEach(link => {
                        const li = link.closest('li');
                        if (li && li.id && li.id.startsWith('product-')) {
                            // Get the first <a> with image
                            const linkWithImg = li.querySelector('a[href*="/prd/"] img')?.closest('a');
                            if (linkWithImg) {
                                const img = linkWithImg.querySelector('img');
                                if (img) {
                                    containers.add(JSON.stringify({
                                        href: linkWithImg.href,
                                        imgSrc: img.src || img.getAttribute('data-src'),
                                        imgAlt: img.alt,
                                        liId: li.id
                                    }));
                                }
                            }
                        }
                    });

                    return Array.from(containers).map(JSON.parse);
                }
            """)

            total_cards = len(product_containers)
            print(f"🔎 Found {total_cards} unique product containers")

            if progress_callback:
                progress_callback({
                    "count": total_cards,
                    "done": False,
                    "message": f"Found {total_cards} products, extracting data..."
                })

            # Show sample product structure
            if len(product_containers) > 0:
                print("🔍 Sample product structure (first product):")
                first = product_containers[0]
                print(f"   Link href: {first['href'][:80]}...")
                print(f"   Image src: {first['imgSrc'][:80] if first['imgSrc'] else 'None'}...")
                print(f"   Image alt: {first['imgAlt']}")

            skipped_count = 0
            skipped_no_url = 0
            skipped_placeholder = 0

            for container in product_containers:
                try:
                    link = container.get('href')
                    img_url = container.get('imgSrc')
                    name = container.get('imgAlt') or "Unnamed Product"

                    if not link:
                        skipped_count += 1
                        continue

                    # Make absolute URL if needed
                    if link.startswith('/'):
                        link = f"https://www.asos.com{link}"

                    # Fix protocol-relative URLs (//images.asos-media.com/...)
                    if img_url and img_url.startswith("//"):
                        img_url = f"https:{img_url}"

                    # Skip if no image URL
                    if not img_url:
                        skipped_no_url += 1
                        skipped_count += 1
                        continue

                    # Skip placeholder images
                    if img_url.startswith("data:"):
                        skipped_placeholder += 1
                        skipped_count += 1
                        continue

                    name = name.strip()

                    # Price extraction - could be added later
                    price = None

                    products.append({
                        "name": name[:100],
                        "link": link,
                        "img_url": img_url,
                        "price": price
                    })

                    # Progress update
                    if progress_callback and len(products) % 20 == 0:
                        progress_callback({
                            "count": len(products),
                            "done": False,
                            "message": f"Extracted {len(products)} products..."
                        })

                except Exception as e:
                    print(f"⚠️ Error extracting product: {e}")
                    skipped_count += 1
                    continue

            browser.close()

            # Print summary
            print(f"\n📊 Extraction Summary:")
            print(f"   Total unique product containers found: {total_cards}")
            print(f"   Products extracted: {len(products)}")
            print(f"   Skipped - no image URL: {skipped_no_url}")
            print(f"   Skipped - placeholder/data URL: {skipped_placeholder}")
            print(f"   Skipped - other: {skipped_count - skipped_no_url - skipped_placeholder}")

            success_rate = ((len(products) / total_cards) * 100) if total_cards > 0 else 0
            print(f"✅ Success rate: {success_rate:.1f}%")

            if progress_callback:
                progress_callback({
                    "count": len(products),
                    "done": True,
                    "message": f"Scraping complete! Found {len(products)} products"
                })

    except Exception as e:
        print(f"❌ Scraper error: {e}")
        if progress_callback:
            progress_callback({"count": 0, "done": True, "message": f"Scraper error: {str(e)}"})

    return {
        "products": products,
        "total_cards": total_cards,
        "unique_products": len(products)
    }


# Convenience function to scrape women's section
def scrape_asos_women(progress_callback=None):
    """Scrape ASOS women's new arrivals"""
    return scrape_asos(
        url="https://www.asos.com/us/women/new-in/new-in-clothing/cat/?cid=27108",
        progress_callback=progress_callback
    )


# Convenience function to scrape men's section
def scrape_asos_men(progress_callback=None):
    """Scrape ASOS men's new arrivals"""
    return scrape_asos(
        url="https://www.asos.com/us/men/new-in/new-in-clothing/cat/?cid=27110",
        progress_callback=progress_callback
    )
