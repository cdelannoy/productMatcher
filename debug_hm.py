"""Debug H&M structure"""
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("🚀 Loading H&M...")
    page.goto("https://www2.hm.com/en_us/ladies/new-arrivals/clothes.html", timeout=60000)

    # Accept cookies
    try:
        page.click("button:has-text('Accept')", timeout=5000)
        print("✅ Accepted cookies")
    except:
        pass

    time.sleep(5)

    # Scroll a bit
    for i in range(3):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)

    print("\n🔍 Looking for product elements...")

    # Try various selectors
    selectors = [
        "article",
        "li.product-item",
        ".product-item",
        "article.item",
        "div[class*='product']",
        "a[href*='/product/']",
        "img[alt*='']"  # All images with alt text
    ]

    for selector in selectors:
        count = len(page.query_selector_all(selector))
        print(f"  {selector}: {count} elements")

    # Get all links
    all_links = page.query_selector_all("a")
    product_links = [l for l in all_links if '/product/' in (l.get_attribute('href') or '')]
    print(f"\n  Links with '/product/': {len(product_links)}")

    if product_links:
        print(f"\n  Sample product links (first 3):")
        for i, link in enumerate(product_links[:3]):
            href = link.get_attribute('href')
            print(f"    {i+1}. {href}")

    # Check page structure
    structure = page.evaluate("""
        () => {
            const main = document.querySelector('main');
            if (!main) return {error: 'No main element'};

            const children = Array.from(main.children).map(el => ({
                tag: el.tagName,
                class: el.className,
                id: el.id,
                childCount: el.children.length
            }));

            return {mainChildren: children.slice(0, 10)};
        }
    """)

    print(f"\n📐 Page structure:")
    print(f"  {structure}")

    # Check what's in those 36 articles
    print("\n🔍 Inspecting article elements...")
    articles = page.query_selector_all("article")
    if articles:
        print(f"  Found {len(articles)} articles")
        first_article = articles[0]

        # Get article HTML (first 500 chars)
        article_html = page.evaluate("(el) => el.outerHTML", first_article)
        print(f"\n  First article HTML (truncated):")
        print(f"  {article_html[:500]}...")

        # Find links and images in article
        article_links = first_article.query_selector_all("a")
        article_images = first_article.query_selector_all("img")
        print(f"\n  First article contains:")
        print(f"    Links: {len(article_links)}")
        print(f"    Images: {len(article_images)}")

        if article_links:
            first_link = article_links[0]
            href = first_link.get_attribute('href')
            print(f"    First link href: {href}")

        if article_images:
            first_img = article_images[0]
            src = first_img.get_attribute('src')
            alt = first_img.get_attribute('alt')
            print(f"    First image src: {src[:80] if src else 'None'}...")
            print(f"    First image alt: {alt}")

    print("\n⏸️  Browser open for inspection (10 seconds)...")
    time.sleep(10)

    browser.close()
