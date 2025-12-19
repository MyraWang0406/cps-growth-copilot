"""Funnel analysis service for Tianchi user behavior data."""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.core.settings import settings
from app.storage.db import Database


class FunnelAnalyzer:
    """Funnel analysis for user behavior data."""
    
    def __init__(self, db: Database):
        """Initialize funnel analyzer."""
        self.db = db
        self._load_rules()
    
    def _load_rules(self):
        """Load funnel rules configuration."""
        config_path = settings.config_dir / "funnel_rules.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.rules = yaml.safe_load(f)
        except FileNotFoundError:
            self.rules = {}
    
    def diagnose(
        self, 
        item_id: str, 
        lookback_days: int = 7
    ) -> Dict[str, Any]:
        """
        Diagnose funnel metrics for an item.
        
        Args:
            item_id: Item ID to analyze
            lookback_days: Number of days to look back
        
        Returns:
            Diagnosis result with metrics and recommendations
        """
        # Calculate time window
        end_time = datetime.now().timestamp()
        start_time = end_time - (lookback_days * 24 * 60 * 60)
        
        # Query user behavior data
        try:
            # Get behavior counts
            behavior_query = """
                SELECT 
                    behavior,
                    COUNT(*) as cnt
                FROM user_behavior
                WHERE item_id = ? 
                  AND timestamp >= ?
                  AND timestamp <= ?
                GROUP BY behavior
            """
            behaviors = self.db.conn.execute(
                behavior_query, 
                [item_id, int(start_time), int(end_time)]
            ).fetchall()
            
            # Convert to dict
            behavior_counts = {row[0]: row[1] for row in behaviors}
            
            pv = behavior_counts.get("pv", 0)
            cart = behavior_counts.get("cart", 0)
            fav = behavior_counts.get("fav", 0)
            buy = behavior_counts.get("buy", 0)
            
            # Calculate conversion rates
            pv_to_cart_rate = (cart / pv * 100) if pv > 0 else 0.0
            cart_to_fav_rate = (fav / cart * 100) if cart > 0 else 0.0
            fav_to_buy_rate = (buy / fav * 100) if fav > 0 else 0.0
            pv_to_buy_rate = (buy / pv * 100) if pv > 0 else 0.0
            
            # Identify drop-off points
            drop_offs = []
            if pv > 0 and pv_to_cart_rate < 5.0:
                drop_offs.append({
                    "stage": "pv_to_cart",
                    "rate": round(pv_to_cart_rate, 2),
                    "threshold": 5.0,
                    "issue": "加购率偏低"
                })
            
            if cart > 0 and cart_to_fav_rate < 10.0:
                drop_offs.append({
                    "stage": "cart_to_fav",
                    "rate": round(cart_to_fav_rate, 2),
                    "threshold": 10.0,
                    "issue": "收藏率偏低"
                })
            
            if fav > 0 and fav_to_buy_rate < 20.0:
                drop_offs.append({
                    "stage": "fav_to_buy",
                    "rate": round(fav_to_buy_rate, 2),
                    "threshold": 20.0,
                    "issue": "购买转化率偏低"
                })
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                pv, cart, fav, buy,
                pv_to_cart_rate, cart_to_fav_rate, fav_to_buy_rate, pv_to_buy_rate
            )
            
            return {
                "item_id": item_id,
                "lookback_days": lookback_days,
                "metrics": {
                    "pv": pv,
                    "cart": cart,
                    "fav": fav,
                    "buy": buy,
                    "pv_to_cart_rate": round(pv_to_cart_rate, 2),
                    "cart_to_fav_rate": round(cart_to_fav_rate, 2),
                    "fav_to_buy_rate": round(fav_to_buy_rate, 2),
                    "pv_to_buy_rate": round(pv_to_buy_rate, 2),
                },
                "drop_offs": drop_offs,
                "recommendations": recommendations,
                "conclusion": self._generate_conclusion(pv, buy, pv_to_buy_rate)
            }
            
        except Exception as e:
            return {
                "item_id": item_id,
                "error": str(e),
                "message": "Could not analyze funnel metrics"
            }
    
    def _generate_recommendations(
        self,
        pv: int, cart: int, fav: int, buy: int,
        pv_to_cart: float, cart_to_fav: float, fav_to_buy: float, pv_to_buy: float
    ) -> List[str]:
        """Generate recommendations based on funnel metrics."""
        recommendations = []
        
        if pv == 0:
            recommendations.append("提升曝光量：增加商品推广和内容营销")
            return recommendations
        
        if pv_to_cart < 5.0:
            recommendations.append("优化商品详情页：提升加购率，改善商品描述和图片")
        
        if cart > 0 and cart_to_fav < 10.0:
            recommendations.append("增强商品吸引力：优化价格策略，增加优惠活动")
        
        if fav > 0 and fav_to_buy < 20.0:
            recommendations.append("促进购买转化：发送优惠提醒，优化购买流程")
        
        if pv_to_buy < 1.0:
            recommendations.append("整体优化：提升商品质量和用户信任度")
        
        if not recommendations:
            recommendations.append("漏斗表现良好，继续保持")
        
        return recommendations
    
    def _generate_conclusion(self, pv: int, buy: int, pv_to_buy: float) -> str:
        """Generate conclusion summary."""
        if pv == 0:
            return "无曝光数据，需要提升商品曝光"
        elif buy == 0:
            return "有曝光但无购买，转化率需要优化"
        elif pv_to_buy < 1.0:
            return f"转化率偏低（{pv_to_buy:.2f}%），存在优化空间"
        elif pv_to_buy < 3.0:
            return f"转化率一般（{pv_to_buy:.2f}%），可进一步提升"
        else:
            return f"转化率良好（{pv_to_buy:.2f}%），表现优秀"


