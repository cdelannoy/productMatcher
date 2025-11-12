"""Debug script to understand ASOS's product loading behavior"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        viewport={'width': 1920, 'height': 1080}
    )
    page = context.new_page()

    print("🚀 Loading ASOS...")
    page.goto("https://www.asos.com/us/women/new-in/new-in-clothing/cat/?cid=27108", timeout=60000)

    # Accept cookies
    try:
        page.click("#onetrust-accept-btn-handler", timeout=5000)
        print("✅ Accepted cookies")
    except:
        pass

    time.sleep(5)

    print("\n📜 Testing scroll behavior...")
    print("=" * 60)

    for i in range(15):
        # Scroll to bottom
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

        # Count products
        link_count = len(page.query_selector_all("a[href*='/prd/']"))

        # Count unique <li> containers
        li_count = page.evaluate("""
            () => {
                const lis = document.querySelectorAll('li[id^="product-"]');
                return lis.length;
            }
        """)

        # Check page height
        page_height = page.evaluate("document.body.scrollHeight")
        scroll_position = page.evaluate("window.scrollY")

        print(f"Scroll #{i+1}:")
        print(f"  Links with /prd/: {link_count}")
        print(f"  <li id='product-*'>: {li_count}")
        print(f"  Page height: {page_height}px")
        print(f"  Scroll position: {scroll_position}px")
        print()

        # Check if there's a "Load More" button or pagination
        load_more = page.query_selector("button:has-text('LOAD MORE')")
        show_more = page.query_selector("button:has-text('Show more')")

        if load_more:
            print("  ⬇️ Found 'LOAD MORE' button - clicking it...")
            load_more.click()
            time.sleep(3)
        elif show_more:
            print("  ⬇️ Found 'Show more' button - clicking it...")
            show_more.click()
            time.sleep(3)

    print("\n" + "=" * 60)
    print("🔍 Looking for pagination/load more mechanisms...")

    # Check for various "load more" button patterns
    load_more_selectors = [
        "button:has-text('LOAD MORE')",
        "button:has-text('Load more')",
        "button:has-text('Show more')",
        "button[data-auto-id='loadMoreProducts']",
        "button.loadMore",
        ".load-more",
        "button:has-text('VIEW MORE')"
    ]

    for selector in load_more_selectors:
        button = page.query_selector(selector)
        if button:
            print(f"  ✅ Found button: {selector}")
            is_visible = page.is_visible(selector)
            print(f"     Visible: {is_visible}")

    # Check for pagination links
    pagination = page.query_selector_all("a[href*='page=']")
    if pagination:
        print(f"  ✅ Found {len(pagination)} pagination links")

    # Look for any buttons at the bottom of the page
    all_buttons = page.query_selector_all("button")
    print(f"  Total buttons on page: {len(all_buttons)}")

    # Get text of buttons near the bottom
    bottom_buttons = page.evaluate("""
        () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.slice(-10).map(b => ({
                text: b.textContent.trim(),
                visible: b.offsetParent !== null
            }));
        }
    """)
    print(f"  Last 10 buttons:")
    for i, btn in enumerate(bottom_buttons, 1):
        if btn['text']:
            print(f"    {i}. '{btn['text']}' (visible: {btn['visible']})")

    print("\n" + "=" * 60)
    print("📊 FINAL COUNT:")
    final_links = len(page.query_selector_all("a[href*='/prd/']"))
    final_lis = page.evaluate("() => document.querySelectorAll('li[id^=\"product-\"]').length")
    print(f"  Total links: {final_links}")
    print(f"  Total <li> containers: {final_lis}")

    # Check if there's text about total products
    product_count_text = page.evaluate("""
        () => {
            const text = document.body.innerText;
            const match = text.match(/(\\d{1,},?\\d+)\\s*(?:items?|products?|styles?)/i);
            return match ? match[0] : null;
        }
    """)

    if product_count_text:
        print(f"  Product count text found on page: '{product_count_text}'")

    print("\n⏸️  Browser will stay open for 10 seconds so you can inspect...")
    time.sleep(10)

    browser.close()
