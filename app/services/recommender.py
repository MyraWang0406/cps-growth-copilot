"""Recommendation engine."""
import yaml
from typing import Dict, Any, Optional
import numpy as np
import math
from datetime import datetime, timezone

from app.core.settings import settings
from app.storage.db import Database
from app.core.guardrails import Guardrails
from app.services.reasons import generate_reasons
from app.services.commission import CommissionService


class Recommender:
    """Recommendation engine with scoring and guardrails."""

    def __init__(self, db: Database, guardrails: Guardrails):
        self.db = db
        self.guardrails = guardrails
        self.commission_service = CommissionService()
        self._load_scoring_config()

    def _load_scoring_config(self):
        config_path = settings.config_dir / "scoring.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            self.scoring_config = yaml.safe_load(f)

    def _norm_category(self, s: Optional[str]) -> str:
        # 让 "All Beauty" / "All_Beauty" 都能匹配
        return (s or "").strip().lower().replace(" ", "_")

    def _normalize_rating(self, rating: Optional[float]) -> float:
        if rating is None:
            return 0.0
        min_rating = self.scoring_config.get("rating_min", 1.0)
        max_rating = self.scoring_config.get("rating_max", 5.0)
        if max_rating == min_rating:
            return 0.0
        return (rating - min_rating) / (max_rating - min_rating)

    def _normalize_popularity(self, count: int) -> float:
        if count <= 0:
            return 0.0
        log_count = np.log1p(count)
        max_log = np.log1p(10000)
        return min(float(log_count / max_log), 1.0) if max_log > 0 else 0.0

    def _calculate_recency_score(self, last_ts_ms: Optional[int]) -> float:
        if last_ts_ms is None:
            return 0.0
        half_life_days = self.scoring_config.get("recency_half_life_days", 180)
        half_life_seconds = half_life_days * 24 * 60 * 60
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_seconds = (now_ms - last_ts_ms) / 1000
        score = 2 ** (-age_seconds / half_life_seconds)
        return min(float(score), 1.0)

    def _calculate_score(self, item: Dict[str, Any]) -> float:
        w_rating = self.scoring_config.get("w_rating", 0.4)
        w_pop = self.scoring_config.get("w_pop", 0.4)
        w_recency = self.scoring_config.get("w_recency", 0.2)

        rating = item.get("avg_rating_review") or item.get("average_rating")
        rating_norm = self._normalize_rating(rating)

        review_cnt = item.get("review_cnt", 0) or 0
        pop_norm = self._normalize_popularity(int(review_cnt))

        last_ts_ms = item.get("last_ts_ms")
        recency_norm = self._calculate_recency_score(last_ts_ms)

        return float(w_rating * rating_norm + w_pop * pop_norm + w_recency * recency_norm)

    # ---- JSON 安全：把 numpy 标量/NaN/Inf 清掉，否则 FastAPI 直接 500 ----
    def _json_safe_scalar(self, v: Any) -> Any:
        if v is None:
            return None

        # numpy scalar -> python scalar
        if isinstance(v, (np.integer,)):
            return int(v)
        if isinstance(v, (np.bool_,)):
            return bool(v)
        if isinstance(v, (np.floating,)):
            v = float(v)

        if isinstance(v, float):
            return v if math.isfinite(v) else None

        return v

    def _sanitize_for_json(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize_for_json(x) for x in obj]
        return self._json_safe_scalar(obj)

    def recommend(
        self,
        query: Optional[str] = None,
        top_n: int = 10,
        category: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
    ) -> Dict[str, Any]:
        # price override
        guardrails = self.guardrails
        if price_min is not None or price_max is not None:
            guardrails = self.guardrails.override_price_range(price_min, price_max)

        max_candidates = self.scoring_config.get("max_candidates", 5000)
        candidates = self.db.search_items(query=query, limit=max_candidates)

        if category:
            want = self._norm_category(category)
            candidates = [
                item for item in candidates
                if self._norm_category(item.get("category") or item.get("main_category")) == want
            ]

        scored_items = []
        for item in candidates:
            score = self._calculate_score(item)
            item["score"] = round(score, 4)

            guardrail_result = guardrails.check(item)
            item["risk_flags"] = guardrail_result["violations"] if not guardrail_result["passed"] else []

            if guardrail_result["passed"]:
                # 先把可能的 NaN/Inf 清一下（避免 reasons 里出现 $nan）
                item = self._sanitize_for_json(item)

                item["reasons"] = generate_reasons(item)

                commission = self.commission_service.calculate_commission(item)
                item["commission_rate"] = commission.get("commission_rate")
                item["estimated_commission"] = commission.get("estimated_commission")
                item["commission_note"] = commission.get("note")

                scored_items.append(item)

        scored_items.sort(key=lambda x: x.get("score", 0), reverse=True)

        passed_total = len(scored_items)
        top_items = scored_items[:top_n]

        filter_stats = guardrails.get_config()

        # 返回前再做一次兜底清洗
        top_items = [self._sanitize_for_json(x) for x in top_items]

        return {
            "query": query or "",
            "category": category,
            "candidates": len(candidates),
            "passed": passed_total,            # 通过 guardrails 的总数
            "returned": len(top_items),        # 实际返回条数（<= top_n）
            "filtered_stats": {
                "min_avg_rating": filter_stats.get("min_avg_rating"),
                "min_rating_count": filter_stats.get("min_rating_count"),
                "price_min": filter_stats.get("price_min"),
                "price_max": filter_stats.get("price_max"),
                "min_review_count": filter_stats.get("min_review_count"),
                "max_days_since_last_review": filter_stats.get("max_days_since_last_review"),
            },
            "items": top_items,
        }
