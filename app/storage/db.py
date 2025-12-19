"""DuckDB storage layer."""
import duckdb
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.settings import DB_PATH


class Database:
    """DuckDB database wrapper."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = DB_PATH
        
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(str(db_path))
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema if tables don't exist."""
        # Items table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                parent_asin TEXT PRIMARY KEY,
                title TEXT,
                price DOUBLE,
                average_rating DOUBLE,
                rating_number BIGINT,
                brand TEXT,
                main_category TEXT,
                categories_json TEXT,
                description_json TEXT
            )
        """)
        
        # Reviews table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                parent_asin TEXT,
                user_id TEXT,
                rating DOUBLE,
                title TEXT,
                text TEXT,
                timestamp_ms BIGINT,
                helpful_vote BIGINT
            )
        """)
        
        # Item stats table (aggregated from reviews)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS item_stats (
                parent_asin TEXT PRIMARY KEY,
                review_cnt BIGINT,
                avg_rating_review DOUBLE,
                last_ts_ms BIGINT
            )
        """)
        
        # User behavior table (Tianchi data)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_behavior (
                user_id TEXT,
                item_id TEXT,
                behavior TEXT,
                timestamp BIGINT,
                category_id TEXT
            )
        """)
        
        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_asin ON reviews(parent_asin)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_items_title ON items(title)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_behavior_item ON user_behavior(item_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_behavior_timestamp ON user_behavior(timestamp)")
    
    def insert_items(self, items: List[Dict[str, Any]]):
        """Insert items into database."""
        if not items:
            return
        
        import pandas as pd
        df = pd.DataFrame(items)
        # Register DataFrame as a temporary table
        self.conn.register("temp_items", df)
        self.conn.execute("""
            INSERT OR REPLACE INTO items 
            SELECT * FROM temp_items
        """)
        self.conn.unregister("temp_items")
    
    def insert_reviews(self, reviews: List[Dict[str, Any]]):
        """Insert reviews into database."""
        if not reviews:
            return
        
        import pandas as pd
        df = pd.DataFrame(reviews)
        # Register DataFrame as a temporary table
        self.conn.register("temp_reviews", df)
        self.conn.execute("""
            INSERT INTO reviews 
            SELECT * FROM temp_reviews
        """)
        self.conn.unregister("temp_reviews")
    
    def build_item_stats(self):
        """Build item_stats table from reviews."""
        self.conn.execute("""
            INSERT OR REPLACE INTO item_stats
            SELECT 
                parent_asin,
                COUNT(*) as review_cnt,
                AVG(rating) as avg_rating_review,
                MAX(timestamp_ms) as last_ts_ms
            FROM reviews
            GROUP BY parent_asin
        """)
    
    def search_items(self, query: Optional[str] = None, limit: int = 5000) -> List[Dict[str, Any]]:
        """Search items by query."""
        if query:
            sql = """
                SELECT i.*, 
                       COALESCE(s.review_cnt, 0) as review_cnt,
                       COALESCE(s.avg_rating_review, i.average_rating) as avg_rating_review,
                       s.last_ts_ms
                FROM items i
                LEFT JOIN item_stats s ON i.parent_asin = s.parent_asin
                WHERE i.title LIKE ?
                LIMIT ?
            """
            pattern = f"%{query}%"
            result = self.conn.execute(sql, [pattern, limit]).fetchdf()
        else:
            sql = """
                SELECT i.*,
                       COALESCE(s.review_cnt, 0) as review_cnt,
                       COALESCE(s.avg_rating_review, i.average_rating) as avg_rating_review,
                       s.last_ts_ms
                FROM items i
                LEFT JOIN item_stats s ON i.parent_asin = s.parent_asin
                LIMIT ?
            """
            result = self.conn.execute(sql, [limit]).fetchdf()
        
        # Convert to dict and handle missing category field
        items = result.to_dict("records")
        for item in items:
            # Ensure category field exists (from items.category or main_category)
            if "category" not in item or item.get("category") is None:
                item["category"] = item.get("main_category")
        return items
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        items_count = self.conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        reviews_count = self.conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        stats_count = self.conn.execute("SELECT COUNT(*) FROM item_stats").fetchone()[0]
        
        top_items = self.conn.execute("""
            SELECT i.parent_asin, i.title, i.price, i.average_rating, 
                   COALESCE(s.review_cnt, 0) as review_cnt
            FROM items i
            LEFT JOIN item_stats s ON i.parent_asin = s.parent_asin
            ORDER BY COALESCE(s.review_cnt, 0) DESC, i.average_rating DESC
            LIMIT 10
        """).fetchdf()
        
        return {
            "items_count": items_count,
            "reviews_count": reviews_count,
            "stats_count": stats_count,
            "top_items": top_items.to_dict("records")
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()

