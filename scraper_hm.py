from playwright.sync_api import sync_playwright
import time
import json

def scrape_hm(url="https://www2.hm.com/en_us/ladies/new-arrivals/clothes.html", progress_callback=None):
    """
    Scraper for H&M e-commerce site.
    H&M has clean structure and fast CDN - ideal for product matching demos.

    Returns a dictionary with:
    - products: list of product dictionaries
    - total_cards: total number of product cards found
    - unique_products: number of unique products
    """
    products = []
    total_cards = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
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

            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            page = context.new_page()

            print(f"🚀 Navigating to H&M: {url}")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"❌ Failed to load page: {e}")
                if progress_callback:
                    progress_callback({"count": 0, "done": True, "message": f"Failed to load page: {str(e)}"})
                return {"products": products, "total_cards": 0, "unique_products": 0}

            if progress_callback:
                progress_callback({"count": 0, "done": False, "message": "Page loaded, waiting for products..."})

            # H&M may have cookie banner
            try:
                # Try different cookie button selectors
                cookie_buttons = [
                    "#onetrust-accept-btn-handler",
                    "button[id*='accept']",
                    "button:has-text('Accept')",
                    "button:has-text('Allow all')"
                ]
                for selector in cookie_buttons:
                    try:
                        page.click(selector, timeout=3000)
                        print("✅ Accepted cookies")
                        break
                    except:
                        continue
            except:
                pass

            # H&M has a promo/newsletter popup with X button in top right - wait for it to appear (1-2 sec delay)
            print("⏳ Waiting for promo popup to appear...")
            time.sleep(3)  # Wait for popup to appear with its delay

            # Try to close the X button in the top right corner
            try:
                close_selectors = [
                    "button[aria-label='Close']",  # Most likely the X button
                    "[class*='parbase'] button[aria-label='Close']",
                    "button.close",
                    "button[title='Close']",
                    "[data-testid='close-button']",
                    ".lightbox-close",
                    ".modal-close"
                ]

                for selector in close_selectors:
                    try:
                        # Wait up to 5 seconds for the close button to be visible
                        page.wait_for_selector(selector, timeout=5000, state="visible")
                        page.click(selector)
                        print("✅ Closed promo popup (clicked X button)")
                        time.sleep(1)  # Wait for popup to close
                        break
                    except:
                        continue
                else:
                    print("⚠️ No close button found, continuing anyway...")
            except Exception as e:
                print(f"⚠️ Could not close popup: {e}")
                pass

            # Wait for products to load
            print("⏳ Waiting for products to load...")
            time.sleep(5)  # Give H&M more time to load products after closing popup

            # Scroll to load products (H&M uses lazy loading)
            print("📜 Scrolling to load products...")
            previous_count = 0
            scroll_attempts = 0
            max_scrolls = 10  # H&M usually loads all products within a few scrolls
            no_change_count = 0

            while scroll_attempts < max_scrolls:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)

                # Count products - H&M uses article elements with data-articlecode
                current_count = page.evaluate("""
                    () => {
                        let items = document.querySelectorAll('article[data-articlecode]');
                        return items.length;
                    }
                """)

                if current_count != previous_count:
                    print(f"  Scroll #{scroll_attempts + 1}: {current_count} products loaded")
                    no_change_count = 0

                    if progress_callback and current_count % 20 == 0:
                        progress_callback({
                            "count": current_count,
                            "done": False,
                            "message": f"Loading products... ({current_count} loaded)"
                        })
                else:
                    no_change_count += 1

                if no_change_count >= 3:
                    print(f"✅ Reached end after {scroll_attempts + 1} scrolls")
                    break

                previous_count = current_count
                scroll_attempts += 1

            # Scroll back to top to ensure all images are visible
            print("📜 Scrolling back to top to load all images...")
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(2)

            # Scroll through one more time slowly to ensure images load
            for i in range(3):
                page.evaluate(f"window.scrollTo(0, {page.evaluate('document.body.scrollHeight') * (i+1) / 3})")
                time.sleep(1)

            # Extract product data using JavaScript
            print("🔍 Extracting product data...")

            product_data = page.evaluate("""
                () => {
                    const products = [];

                    // H&M uses article elements with data-articlecode attribute
                    const productElements = document.querySelectorAll('article[data-articlecode]');

                    productElements.forEach(element => {
                        try {
                            // Find link - H&M uses /en_us/productpage.*
                            const link = element.querySelector('a[href*="/productpage"]') || element.querySelector('a');
                            if (!link) {
                                console.log('No link found');
                                return;
                            }

                            // Find image
                            const img = element.querySelector('img');
                            if (!img) {
                                console.log('No image found');
                                return;
                            }

                            // Get image URL - try multiple attributes
                            let imgSrc = img.src || img.getAttribute('srcset')?.split(',')[0]?.trim()?.split(' ')[0] || img.getAttribute('data-src');

                            // Get product name from alt text or title
                            const name = img.alt || link.getAttribute('title') || link.getAttribute('aria-label') || 'Unnamed Product';

                            // Get product link (convert relative to absolute)
                            let href = link.href;
                            if (href.startsWith('/')) {
                                href = 'https://www2.hm.com' + href;
                            }

                            // Add product even if imgSrc might be placeholder - we'll filter later
                            products.push({
                                name: name,
                                link: href,
                                imgSrc: imgSrc || ''
                            });
                        } catch (e) {
                            console.log('Error:', e);
                        }
                    });

                    return products;
                }
            """)

            total_cards = len(product_data)
            print(f"🔎 Found {total_cards} products")

            if progress_callback:
                progress_callback({
                    "count": total_cards,
                    "done": False,
                    "message": f"Found {total_cards} products, processing..."
                })

            # Show sample
            if len(product_data) > 0:
                print("🔍 Sample product (first):")
                first = product_data[0]
                print(f"   Name: {first['name'][:60]}...")
                print(f"   Link: {first['link'][:80]}...")
                print(f"   Image: {first['imgSrc'][:80]}...")

            skipped_count = 0

            for item in product_data:
                try:
                    name = item['name'].strip()
                    link = item['link']
                    img_url = item['imgSrc']

                    # Make absolute URL if needed
                    if link.startswith('/'):
                        link = f"https://www2.hm.com{link}"

                    # Fix protocol-relative URLs
                    if img_url.startswith('//'):
                        img_url = f"https:{img_url}"

                    # Skip if no valid image URL
                    if not img_url or img_url.startswith('data:'):
                        skipped_count += 1
                        continue

                    products.append({
                        "name": name[:100],
                        "link": link,
                        "img_url": img_url,
                        "price": None
                    })

                    if progress_callback and len(products) % 10 == 0:
                        progress_callback({
                            "count": len(products),
                            "done": False,
                            "message": f"Processed {len(products)} products..."
                        })

                except Exception as e:
                    print(f"⚠️ Error processing product: {e}")
                    skipped_count += 1
                    continue

            browser.close()

            print(f"\n📊 Extraction Summary:")
            print(f"   Total products found: {total_cards}")
            print(f"   Products extracted: {len(products)}")
            print(f"   Skipped: {skipped_count}")

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


# Convenience functions
def scrape_hm_women_new(progress_callback=None):
    """Scrape H&M women's new arrivals"""
    return scrape_hm(
        url="https://www2.hm.com/en_us/ladies/new-arrivals/clothes.html",
        progress_callback=progress_callback
    )


def scrape_hm_men_new(progress_callback=None):
    """Scrape H&M men's new arrivals"""
    return scrape_hm(
        url="https://www2.hm.com/en_us/men/new-arrivals/clothes.html",
        progress_callback=progress_callback
    )
