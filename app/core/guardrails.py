"""Guardrails system for filtering recommendations."""
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from app.core.settings import settings


class Guardrails:
    """Guardrails for recommendation filtering."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize guardrails from config file."""
        if config_path is None:
            config_path = settings.config_dir / "guardrails.yaml"
        
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def check(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if item passes guardrails.
        
        Returns:
            {
                "passed": bool,
                "violations": List[str]
            }
        """
        violations = []
        
        # Check average rating
        avg_rating = item.get("average_rating")
        if avg_rating is not None:
            min_rating = self.config.get("min_avg_rating", 0.0)
            if avg_rating < min_rating:
                violations.append(f"Average rating {avg_rating:.2f} below minimum {min_rating}")
        
        # Check rating count
        rating_count = item.get("rating_number", 0)
        min_count = self.config.get("min_rating_count", 0)
        if rating_count < min_count:
            violations.append(f"Rating count {rating_count} below minimum {min_count}")
        
        # Check review count (from stats)
        review_count = item.get("review_cnt", 0)
        min_review_count = self.config.get("min_review_count", 0)
        if review_count < min_review_count:
            violations.append(f"Review count {review_count} below minimum {min_review_count}")
        
        # Check price
        price = item.get("price")
        if price is not None:
            try:
                price_float = float(price)
                price_min = self.config.get("price_min", 0.0)
                price_max = self.config.get("price_max", float("inf"))
                
                if price_float < price_min:
                    violations.append(f"Price {price_float:.2f} below minimum {price_min}")
                if price_float > price_max:
                    violations.append(f"Price {price_float:.2f} above maximum {price_max}")
            except (ValueError, TypeError):
                violations.append(f"Invalid price value: {price}")
        
        # Check banned brands
        brand = item.get("brand", "")
        if brand:
            banned_brands = [b.lower() for b in self.config.get("banned_brands", [])]
            if brand.lower() in banned_brands:
                violations.append(f"Brand '{brand}' is banned")
        
        # Check banned ASINs
        asin = item.get("parent_asin", "")
        banned_asins = self.config.get("banned_asins", [])
        if asin in banned_asins:
            violations.append(f"ASIN '{asin}' is banned")
        
        # Check banned categories
        category = item.get("category") or item.get("main_category", "")
        if category:
            banned_categories = [c.lower() for c in self.config.get("banned_categories", [])]
            if category.lower() in banned_categories:
                violations.append(f"Category '{category}' is banned")
        
        # Check recency (if last_ts_ms is available)
        last_ts_ms = item.get("last_ts_ms")
        if last_ts_ms is not None:
            max_days = self.config.get("max_days_since_last_review", 3650)
            days_ago = (datetime.now(timezone.utc).timestamp() * 1000 - last_ts_ms) / (1000 * 60 * 60 * 24)
            if days_ago > max_days:
                violations.append(f"Last review was {days_ago:.0f} days ago, exceeds {max_days} days")
        
        return {
            "passed": len(violations) == 0,
            "violations": violations
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get current guardrails configuration."""
        return self.config.copy()
    
    def override_price_range(self, price_min: Optional[float] = None, price_max: Optional[float] = None) -> "Guardrails":
        """Create a new Guardrails instance with overridden price range."""
        new_config = self.config.copy()
        if price_min is not None:
            new_config["price_min"] = price_min
        if price_max is not None:
            new_config["price_max"] = price_max
        
        # Create a temporary guardrails instance
        temp_guardrails = Guardrails.__new__(Guardrails)
        temp_guardrails.config = new_config
        return temp_guardrails

