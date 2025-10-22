---
title: Product Matcher
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: apache-2.0
short_description: AI visual search to find similar products using CLIP
---

# Product Matcher by L'Optimist

An AI-powered visual product search engine that finds similar items on e-commerce websites. Upload any product image and let CLIP (OpenAI's vision model) find visually similar products for you.

## Features

- **Visual Product Search**: Upload any product image to find similar items
- **AI-Powered Matching**: Uses OpenAI's CLIP model for intelligent visual similarity
- **Multi-Scale Analysis**: Advanced matching algorithm analyzes images at multiple scales
- **Diversity Re-Ranking**: Returns diverse results to avoid showing near-duplicate items
- **Real-Time Progress**: Live updates during scraping and matching process
- **E-Commerce Integration**: Built-in scraper for Tommy Hilfiger and adaptable to other sites

## Technology Stack

- **Flask**: Web framework for the application
- **PyTorch + CLIP**: Deep learning model for visual similarity
- **Playwright**: Automated web scraping with Chromium
- **PIL (Pillow)**: Image processing and manipulation
- **Docker**: Containerized deployment

## Quick Start

This app is designed to run on **Hugging Face Spaces** with Docker. For local development:

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/cdelannoy/productMatcher.git
cd productMatcher
```

2. **Create and activate a virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
playwright install chromium
```

4. **Run the app:**
```bash
python app.py
```

5. **Open in browser:**
```
http://localhost:5000
```

### Docker Deployment

```bash
docker build -t product-matcher .
docker run -p 5000:7860 product-matcher
```

## How to Use

1. **Upload an Image**: Choose a product image you want to find matches for
2. **Set Top X**: Select how many similar products you want to see (default: 5)
3. **Target URL**: Use the default (Tommy Hilfiger) or enter a different e-commerce site
4. **Search**: Click search and watch real-time progress as the app works
5. **View Results**: See the most similar products with similarity scores

## How It Works

### 1. Web Scraping
The app uses Playwright with Chromium to:
- Navigate to the target e-commerce website
- Accept cookies and handle popups
- Scroll through the page to load lazy-loaded content
- Extract product names, images, and links

### 2. Multi-Scale Embeddings
For both the query image and each product:
- Generate CLIP embeddings at multiple scales (global, regions, crops)
- Capture both overall appearance and fine details
- Create comprehensive visual representations

### 3. Advanced Similarity Matching
- Compute weighted similarity scores across all scales
- Combine global similarity with regional matches
- Rank products by visual similarity to the query image

### 4. Diversity Re-Ranking
- Filter out near-duplicate results
- Ensure diverse product recommendations
- Return the top X most relevant and varied matches

## Configuration

### Adapting to Other Websites

The scraper is configured for Tommy Hilfiger by default. To adapt for other sites:

1. Open [scraper.py](scraper.py)
2. Update the CSS selectors for product elements (line ~47)
3. Adjust image extraction logic (lines ~59-64)
4. Modify scroll behavior if needed (lines ~36-39)

### Performance Tuning

- **Scraping speed**: Adjust `max_scrolls` and `time.sleep()` in [scraper.py](scraper.py)
- **Matching accuracy**: Modify diversity weight in [improved_matcher.py](improved_matcher.py)
- **Memory usage**: Consider reducing batch size for large product catalogs

## Use Cases

- **Fashion Retail**: Find similar clothing items across different brands
- **Interior Design**: Match furniture and decor pieces
- **Market Research**: Analyze product positioning and visual trends
- **Personal Shopping**: Help customers discover alternatives and variations

## Notes

- The CLIP model (~350MB) downloads automatically on first run
- Playwright installs Chromium browser for web scraping
- Processing time varies based on the number of products on the target page
- For production use, consider rate limiting and respecting robots.txt

## License

ISC

## Author

Constance Delannoy | [L'Optimist](https://l-optimist.com)

---

*Built with Flask, PyTorch, and OpenAI's CLIP model*
