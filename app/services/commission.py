"""Commission calculation service."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.settings import settings


class CommissionService:
    """Commission calculation service."""
    
    def __init__(self):
        """Initialize commission service."""
        self._load_config()
    
    def _load_config(self):
        """Load commission configuration."""
        config_path = settings.config_dir / "commission.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
    
    def calculate_commission(
        self, 
        item: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate commission rate and estimated commission for an item.
        
        Args:
            item: Item dictionary with price, category, etc.
        
        Returns:
            Dictionary with commission_rate and estimated_commission
        """
        price = item.get("price")
        if price is None:
            return {
                "commission_rate": self.config.get("default_rate", 0.10),
                "estimated_commission": 0.0,
                "note": "simulated"
            }
        
        try:
            price_float = float(price)
        except (ValueError, TypeError):
            return {
                "commission_rate": self.config.get("default_rate", 0.10),
                "estimated_commission": 0.0,
                "note": "simulated"
            }
        
        # Try category-based rate first
        category = item.get("category") or item.get("main_category")
        rate = None
        
        if category:
            category_rates = self.config.get("category_rates", {})
            rate = category_rates.get(category)
        
        # If no category match, try price range
        if rate is None:
            price_ranges = self.config.get("price_range_rates", [])
            for pr in price_ranges:
                if pr["min_price"] <= price_float < pr["max_price"]:
                    rate = pr["rate"]
                    break
        
        # Fallback to default
        if rate is None:
            rate = self.config.get("default_rate", 0.10)
        
        estimated_commission = price_float * rate
        
        return {
            "commission_rate": rate,
            "estimated_commission": round(estimated_commission, 2),
            "note": "simulated"  # Explicitly mark as simulated
        }


