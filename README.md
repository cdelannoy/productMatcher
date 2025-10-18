# Product Matcher App

A Flask-based web application that uses AI image matching to find the most relevant products from a website based on an uploaded image. The app scrapes product listings from a specified URL and uses OpenAI's CLIP model to find visually similar products.

## Features

- Upload an image to search for similar products
- Scrape products from e-commerce websites
- Real-time progress updates during scraping and matching
- Visual similarity scoring using CLIP embeddings
- Configurable number of top matches to display

## Important Note: Browser Visibility

To bypass bot detection on sites like Tommy Hilfiger, the scraper runs with a **visible browser window** (non-headless mode). This is necessary because many e-commerce sites block headless browsers.

**What this means:**
- A Chrome browser window will open and be visible during scraping
- The browser will automatically close when scraping is complete
- Do not close the browser window manually while scraping is in progress

**Working sites:**
- https://usa.tommy.com/en/women (requires non-headless mode)
- https://www.scrapingcourse.com/ecommerce/ (demo site)
- Most e-commerce sites work with non-headless mode

For production use in the background, consider using official APIs provided by e-commerce platforms instead of web scraping.

## Requirements

- Python 3.8+
- Node.js (for Playwright browser automation)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/cdelannoy/webTommy.git
cd webTommy
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

**Note**: If you encounter an SSL certificate error when installing CLIP, you may need to uninstall the wrong `clip` package and install the correct one:
```bash
pip uninstall -y clip
pip install git+https://github.com/openai/CLIP.git
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Upload an image of a product you want to find
4. Specify the number of matches you want (default: 5)
5. Enter the URL of the website to search (default: Tommy Hilfiger women's section)
6. Click "Search" and wait for the results

## How It Works

1. **Image Upload**: User uploads a reference image
2. **Web Scraping**: The app uses Playwright to:
   - Navigate to the specified URL
   - Accept cookies
   - Scroll through the page to load all lazy-loaded products
   - Extract product names, images, and links
3. **Image Matching**: For each product:
   - Download the product image
   - Generate CLIP embeddings for both the reference and product images
   - Calculate cosine similarity between embeddings
4. **Display Results**: Show the top N most similar products with their similarity scores

## Configuration

### Changing the Target Website

The scraper is configured for Tommy Hilfiger's website by default. To adapt it for other websites:

1. Open [scraper.py](scraper.py)
2. Modify the CSS selector in line 47: `a.pdpurl` to match the product elements on your target site
3. Adjust the image selector logic (lines 59-64) to match your target site's structure

### Adjusting Scraping Behavior

- **Scroll wait time**: Modify `time.sleep(5)` in [scraper.py:39](scraper.py#L39) to adjust pause between scrolls
- **Max scrolls**: Change `max_scrolls = 20` in [scraper.py:36](scraper.py#L36) to limit scrolling
- **Progress updates**: Adjust the frequency in [scraper.py:75](scraper.py#L75) (currently every 10 products)

### Matching Settings

- **Timeout for image downloads**: Change `timeout=10` in [app.py:99](app.py#L99)
- **Progress update frequency**: Modify the interval in [app.py:106](app.py#L106) (currently every 5 products)

## Troubleshooting

### Playwright Installation Issues

If you encounter issues with Playwright:
```bash
playwright install-deps
playwright install chromium
```

### CLIP Model Issues

The CLIP model will be downloaded on first run. Ensure you have a stable internet connection and sufficient disk space (~350MB).

### Scraping Issues

If the scraper returns no products:
- Check that the target URL is accessible
- Verify the CSS selectors match the website's structure
- Try increasing the scroll wait time in [scraper.py](scraper.py)

## License

ISC

## Author

Constance Delannoy
