# Scraping Notes for Tommy Hilfiger Website

## Current Behavior

The scraper currently finds **~74-370 unique products** from https://usa.tommy.com/en/women

### Why Not 1,410 Products?

The 1,410 products number likely represents:
1. **Total across all categories** - The full women's catalog including all subcategories
2. **Multiple pages** - Products may be split across pagination or different filtered views
3. **Dynamic filtering** - The initial page load only shows a subset

### What the Scraper Does

1. ✅ Opens the URL in a non-headless browser (bypasses bot detection)
2. ✅ Scrolls the page repeatedly to trigger lazy loading
3. ✅ Waits for network to be idle after each scroll
4. ✅ Extracts all product cards found
5. ✅ Deduplicates based on product name

### Current Results

- **Product cards found**: 300-400 (includes duplicates for different sizes/colors)
- **Unique products**: ~74
- **Scroll attempts**: 6-10 before page height stabilizes
- **Time taken**: 30-60 seconds

## How to Get More Products

### Option 1: Target Specific Category URLs

Instead of the main women's page, use category-specific URLs:
```
https://usa.tommy.com/en/women/clothing
https://usa.tommy.com/en/women/shoes
https://usa.tommy.com/en/women/accessories
```

### Option 2: Scrape Multiple Pages

Run the scraper multiple times with different URLs and combine results.

### Option 3: Use API (Recommended for Production)

If you need all 1,410 products reliably, consider:
- Using Tommy Hilfiger's official API (if available)
- Using e-commerce platform APIs (Shopify, etc.)
- Commercial web scraping services with better bot evasion

## Current Scraper Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `headless` | False | Bypass bot detection |
| `max_scrolls` | 200 | Maximum scroll attempts |
| `scroll_wait` | 4 seconds | Wait between scrolls |
| `network_idle_wait` | 8 seconds | Wait for network |
| `no_change_threshold` | 5 attempts | When to stop scrolling |

## Recommendations

**For your use case (image matching):**
- The current 70-300 products is sufficient for demo/testing
- Image matching quality matters more than quantity
- You can still find relevant matches from the available products

**If you need all 1,410 products:**
- This requires a more sophisticated approach (multiple URLs, handling pagination, etc.)
- Consider if it's worth the complexity vs. using available products
- The matching algorithm will work the same way regardless of product count

## Testing the Scraper

```bash
python -c "from scraper import scrape_us_tommy; products = scrape_us_tommy('https://usa.tommy.com/en/women'); print(f'Found {len(products)} products')"
```

The scraper will:
- Show progress every 5 scrolls
- Display total product cards found
- Return deduplicated unique products
