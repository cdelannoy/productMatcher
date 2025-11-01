"""
Improved image matching algorithms for better product recommendations.
"""
import torch
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from typing import List, Dict, Tuple
import clip

def get_multi_scale_embeddings(image, model, preprocess, device):
    """
    Extract embeddings at multiple scales and transformations for better matching.
    Helps capture both fine details, overall composition, and different viewing conditions.
    """
    embeddings = []

    # 1. Original image (full context)
    img_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img_input)
        embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

    # 2. Center crop (focus on main object)
    width, height = image.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    center_crop = image.crop((left, top, left + min_dim, top + min_dim))

    img_input = preprocess(center_crop).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img_input)
        embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

    # 3. Enhanced contrast (helps with lighting differences)
    enhancer = ImageEnhance.Contrast(image)
    contrast_img = enhancer.enhance(1.5)
    img_input = preprocess(contrast_img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img_input)
        embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

    # 4. Brightness adjusted (helps with dark/light variations)
    brightness_enhancer = ImageEnhance.Brightness(image)
    bright_img = brightness_enhancer.enhance(1.3)
    img_input = preprocess(bright_img).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img_input)
        embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

    # 5. Slightly blurred (helps match with different image quality)
    blurred = image.filter(ImageFilter.GaussianBlur(radius=1))
    img_input = preprocess(blurred).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(img_input)
        embeddings.append(emb / emb.norm(dim=-1, keepdim=True))

    return embeddings


def compute_advanced_similarity(query_embeddings, product_embeddings, query_text_emb=None, product_name="", text_weight=0.3):
    """
    Compute similarity using multiple strategies and combine them.

    Returns a weighted score that considers:
    1. Maximum similarity across scales (image-based)
    2. Average similarity (image-based)
    3. Text-based semantic similarity (if product name provided)
    """
    similarities = []

    for q_emb in query_embeddings:
        for p_emb in product_embeddings:
            sim = torch.cosine_similarity(q_emb, p_emb).item()
            similarities.append(sim)

    similarities = np.array(similarities)

    # Combine different metrics
    max_sim = np.max(similarities)  # Best match across scales
    avg_sim = np.mean(similarities)  # Overall similarity
    min_sim = np.min(similarities)  # Worst case (for consistency)

    # Image-based score
    image_score = (
        0.5 * max_sim +
        0.35 * avg_sim +
        0.15 * min_sim
    )

    # Add text-based boosting if available
    if query_text_emb is not None and product_name:
        # Generate text features for product
        product_tokens = clip.tokenize([product_name])
        # Note: Need to pass device, will be handled in calling function
        text_sim = 0  # Placeholder, computed in main loop

        # Hybrid score combines image and text
        final_score = (1 - text_weight) * image_score + text_weight * text_sim
        return final_score

    return image_score


def extract_color_features(image):
    """
    Extract dominant colors from image for color-based filtering/boosting.
    """
    # Resize for faster processing
    img_small = image.resize((100, 100))
    pixels = np.array(img_small).reshape(-1, 3)

    # Get mean color
    mean_color = pixels.mean(axis=0)

    # Get color variance (how colorful vs monochrome)
    color_variance = pixels.std(axis=0).mean()

    return {
        'mean_color': mean_color,
        'color_variance': color_variance
    }


def color_similarity_boost(query_features, product_features):
    """
    Boost score if colors are similar (optional enhancement).
    """
    query_color = query_features['mean_color']
    product_color = product_features['mean_color']

    # Euclidean distance in RGB space
    color_distance = np.linalg.norm(query_color - product_color)

    # Normalize to 0-1 range (assuming max distance ~440 in RGB)
    color_similarity = 1 - (color_distance / 440)

    return max(0, color_similarity)


def rerank_with_diversity(results, top_k=5, diversity_weight=0.3):
    """
    Re-rank results to balance similarity with diversity.
    Prevents returning 5 very similar items.
    """
    if len(results) <= top_k:
        return results

    selected = []
    remaining = results.copy()

    # Always take the top result
    selected.append(remaining.pop(0))

    while len(selected) < top_k and remaining:
        best_score = -float('inf')
        best_idx = 0

        for idx, candidate in enumerate(remaining):
            # Original similarity score
            sim_score = candidate['score']

            # Diversity penalty (how different from already selected)
            diversity_penalty = 0
            for selected_item in selected:
                # Simple diversity: penalize if product names are too similar
                name_overlap = len(set(candidate['product']['name'].lower().split()) &
                                  set(selected_item['product']['name'].lower().split()))
                diversity_penalty += name_overlap / 10  # Normalize

            # Combined score
            combined = sim_score - (diversity_weight * diversity_penalty)

            if combined > best_score:
                best_score = combined
                best_idx = idx

        selected.append(remaining.pop(best_idx))

    return selected


def get_text_embedding(text, model, device):
    """
    Get CLIP text embedding for text-based matching.
    Can be used to boost products that match the query semantically.
    """
    text_tokens = clip.tokenize([text]).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
    return text_features


def compute_hybrid_similarity(query_image_embeddings, product_image_embeddings,
                               query_text_emb, product_name, model, device, text_weight=0.4):
    """
    Compute hybrid similarity combining image and text-based matching.
    This is more robust for CLIP and helps find semantically similar products.
    """
    # Image similarity
    image_similarities = []
    for q_emb in query_image_embeddings:
        for p_emb in product_image_embeddings:
            sim = torch.cosine_similarity(q_emb, p_emb).item()
            image_similarities.append(sim)

    image_similarities = np.array(image_similarities)
    max_img_sim = np.max(image_similarities)
    avg_img_sim = np.mean(image_similarities)

    # Image score (70% weight internally)
    image_score = 0.7 * max_img_sim + 0.3 * avg_img_sim

    # Text similarity (compare query image meaning with product name)
    product_text_emb = get_text_embedding(product_name, model, device)
    text_sim = torch.cosine_similarity(query_text_emb, product_text_emb).item()

    # Hybrid score: balance image and text
    final_score = (1 - text_weight) * image_score + text_weight * text_sim

    return final_score


def match_with_text_boost(image_score, product_name, query_text, text_embedding, model, device, boost_weight=0.2):
    """
    Optionally boost score if product name semantically matches a text query.
    Useful if user provides description like "red dress" or "winter coat".
    """
    if not query_text or not query_text.strip():
        return image_score

    # Get product name embedding
    product_text_emb = get_text_embedding(product_name, model, device)

    # Compute text similarity
    text_sim = torch.cosine_similarity(text_embedding, product_text_emb).item()

    # Boost image score based on text match
    boosted_score = image_score + (boost_weight * text_sim)

    return boosted_score
