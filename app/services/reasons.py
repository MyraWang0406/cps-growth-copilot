"""Reason generation for explainability."""
from typing import Dict, Any, List
from datetime import datetime, timezone


def generate_reasons(item: Dict[str, Any]) -> List[str]:
    """
    Generate 2-3 human-readable reasons for why an item was recommended.
    
    Args:
        item: Item dictionary with fields like average_rating, review_cnt, etc.
    
    Returns:
        List of 2-3 reason strings (prioritized)
    """
    reasons = []
    
    # Priority 1: Rating (if good)
    avg_rating = item.get("avg_rating_review") or item.get("average_rating")
    if avg_rating is not None and avg_rating >= 4.0:
        reasons.append(f"评分高（{avg_rating:.1f}分）")
    
    # Priority 2: Review count (popularity)
    review_cnt = item.get("review_cnt", 0)
    rating_number = item.get("rating_number", 0)
    total_reviews = max(review_cnt, rating_number)
    if total_reviews >= 50:
        reasons.append(f"评论多（{total_reviews}条）")
    elif total_reviews >= 10:
        reasons.append(f"评论数适中（{total_reviews}条）")
    
    # Priority 3: Price range match
    price = item.get("price")
    if price is not None:
        try:
            price_float = float(price)
            if 10 <= price_float <= 100:
                reasons.append(f"价格带匹配（${price_float:.2f}）")
            else:
                reasons.append(f"价格 ${price_float:.2f}")
        except (ValueError, TypeError):
            pass
    
    # Priority 4: Category match
    category = item.get("category") or item.get("main_category")
    if category and len(reasons) < 3:
        reasons.append(f"类目匹配（{category}）")
    
    # Ensure we return 2-3 reasons
    if len(reasons) == 0:
        reasons.append("商品信息完整")
    if len(reasons) == 1:
        # Add a generic reason
        if avg_rating is not None:
            reasons.append(f"评分 {avg_rating:.1f}")
        elif total_reviews > 0:
            reasons.append(f"有 {total_reviews} 条评价")
        else:
            reasons.append("商品可用")
    
    return reasons[:3]  # Return max 3 reasons

