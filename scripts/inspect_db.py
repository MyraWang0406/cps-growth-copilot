"""Inspect database contents."""
import argparse
import sys
from pathlib import Path
import duckdb


def main():
    """Print database statistics."""
    parser = argparse.ArgumentParser(description="Inspect DuckDB database contents")
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to DuckDB database file (default: use unified DB_PATH)"
    )
    args = parser.parse_args()
    
    # Use unified DB path
    if args.db:
        db_path = Path(args.db)
    else:
        # Get repo root (assuming script is in scripts/ directory)
        repo_root = Path(__file__).resolve().parent.parent
        db_path = repo_root / "data" / "duckdb" / "cps_growth.duckdb"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}", file=sys.stderr)
        print(f"   Absolute path: {db_path.absolute()}", file=sys.stderr)
        print("   Run bootstrap_data.py first to create the database.", file=sys.stderr)
        sys.exit(1)
    
    con = duckdb.connect(str(db_path))
    
    print("="*50)
    print("Database Statistics")
    print("="*50)
    print(f"DB (relative): {db_path}")
    print(f"DB (absolute): {db_path.absolute()}\n")
    
    # Show all tables
    try:
        tables_result = con.execute("SHOW TABLES").fetchall()
        if tables_result:
            print("Tables in database:")
            for row in tables_result:
                print(f"  - {row[0]}")
        else:
            print("⚠️  No tables found in database")
        print()
    except Exception as e:
        print(f"⚠️  Could not list tables: {e}\n")
    
    # Check and count items table
    items_count = None
    try:
        items_count = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        print(f"Items: {items_count}")
    except Exception as e:
        if "does not exist" in str(e).lower() or "table" in str(e).lower():
            print("❌ Table 'items' does not exist")
        else:
            print(f"❌ Error querying items table: {e}")
    
    # Check and count reviews table
    reviews_count = None
    try:
        reviews_count = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        print(f"Reviews: {reviews_count}")
    except Exception as e:
        if "does not exist" in str(e).lower() or "table" in str(e).lower():
            print("❌ Table 'reviews' does not exist")
        else:
            print(f"❌ Error querying reviews table: {e}")
    
    # Check and count item_stats table (if exists)
    try:
        stats_count = con.execute("SELECT COUNT(*) FROM item_stats").fetchone()[0]
        print(f"Item Stats: {stats_count}")
    except Exception as e:
        if "does not exist" in str(e).lower() or "table" in str(e).lower():
            print("⚠️  Table 'item_stats' does not exist (this is optional)")
        else:
            print(f"⚠️  Error querying item_stats table: {e}")
    
    # Summary
    if items_count is not None and reviews_count is not None:
        if items_count == 0 and reviews_count == 0:
            print("\n⚠️  Database is empty. Run bootstrap_data.py to import data.")
        elif items_count > 0 or reviews_count > 0:
            print(f"\n✅ Database contains data: {items_count} items, {reviews_count} reviews")
    
    # Get top items (only if items table exists and has data)
    if items_count and items_count > 0:
        try:
            top_items = con.execute("""
                SELECT 
                    i.parent_asin,
                    i.title,
                    i.price,
                    i.average_rating,
                    COUNT(r.parent_asin) as review_cnt
                FROM items i
                LEFT JOIN reviews r ON i.parent_asin = r.parent_asin
                GROUP BY i.parent_asin, i.title, i.price, i.average_rating
                ORDER BY review_cnt DESC, i.average_rating DESC
                LIMIT 10
            """).fetchall()
            
            if top_items:
                print("\nTop 10 items by review count:")
                print("-" * 50)
                for i, row in enumerate(top_items, 1):
                    asin, title, price, rating, review_cnt = row
                    print(f"\n{i}. ASIN: {asin}")
                    if title:
                        print(f"   Title: {title[:60]}...")
                    print(f"   Price: ${price:.2f}" if price else "   Price: N/A")
                    print(f"   Rating: {rating:.2f}" if rating else "   Rating: N/A")
                    print(f"   Reviews: {review_cnt}")
        except Exception as e:
            print(f"\n⚠️  Could not fetch top items: {e}")
    
    con.close()


if __name__ == "__main__":
    main()

