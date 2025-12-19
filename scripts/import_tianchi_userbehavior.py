"""Import Tianchi UserBehavior data."""
import argparse
import csv
import sys
from pathlib import Path
import duckdb
from tqdm import tqdm


def _db_path() -> Path:
    """Get unified DB path (relative to repo root)."""
    repo_root = Path(__file__).resolve().parent.parent
    p = repo_root / "data" / "duckdb" / "cps_growth.duckdb"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def main():
    """Import Tianchi UserBehavior CSV to DuckDB."""
    parser = argparse.ArgumentParser(description="Import Tianchi UserBehavior data")
    parser.add_argument(
        "--csv-path", 
        type=str, 
        default="data/raw/tianchi/UserBehavior.csv",
        help="Path to UserBehavior.csv file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of rows to import (for testing)"
    )
    args = parser.parse_args()
    
    csv_path = Path(args.csv_path)
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}", file=sys.stderr)
        print(f"   Absolute path: {csv_path.absolute()}", file=sys.stderr)
        print("   Please download UserBehavior.csv from Tianchi and place it in data/raw/tianchi/", file=sys.stderr)
        sys.exit(1)
    
    print("="*50)
    print("Tianchi UserBehavior Import")
    print("="*50)
    print(f"CSV file: {csv_path}")
    
    # Connect to database
    db_path = _db_path()
    con = duckdb.connect(str(db_path))
    
    # Ensure schema exists
    con.execute("""
        CREATE TABLE IF NOT EXISTS user_behavior (
            user_id TEXT,
            item_id TEXT,
            behavior TEXT,
            timestamp BIGINT,
            category_id TEXT
        )
    """)
    
    # Clear existing data (optional)
    con.execute("DELETE FROM user_behavior")
    
    # Read and import CSV
    print("\nReading CSV file...")
    rows = []
    imported = 0
    
    try:
        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            delimiter = "," if sample.count(",") > sample.count("\t") else "\t"
            
            reader = csv.reader(f, delimiter=delimiter)
            
            # Skip header if present
            first_row = next(reader, None)
            if first_row and not first_row[0].isdigit():
                # Likely header row
                print(f"Detected header: {first_row}")
            else:
                # No header, process first row
                if first_row:
                    rows.append(first_row)
            
            # Process rows
            for row in tqdm(reader, desc="Reading CSV"):
                if args.limit and imported >= args.limit:
                    break
                
                if len(row) < 5:
                    continue
                
                try:
                    user_id = str(row[0]).strip()
                    item_id = str(row[1]).strip()
                    category_id = str(row[2]).strip()
                    behavior = str(row[3]).strip().lower()  # Normalize to lowercase
                    timestamp_str = str(row[4]).strip()
                    
                    # Parse timestamp (assume Unix timestamp in seconds)
                    try:
                        timestamp = int(float(timestamp_str))
                    except (ValueError, TypeError):
                        continue
                    
                    # Validate behavior type
                    if behavior not in ["pv", "cart", "fav", "buy"]:
                        continue
                    
                    rows.append((user_id, item_id, behavior, timestamp, category_id))
                    imported += 1
                    
                    # Batch insert
                    if len(rows) >= 10000:
                        con.executemany("""
                            INSERT INTO user_behavior(user_id, item_id, behavior, timestamp, category_id)
                            VALUES (?, ?, ?, ?, ?)
                        """, rows)
                        rows.clear()
                        
                except Exception as e:
                    continue
        
        # Insert remaining rows
        if rows:
            con.executemany("""
                INSERT INTO user_behavior(user_id, item_id, behavior, timestamp, category_id)
                VALUES (?, ?, ?, ?, ?)
            """, rows)
        
        # Get statistics
        total_rows = con.execute("SELECT COUNT(*) FROM user_behavior").fetchone()[0]
        behavior_stats = con.execute("""
            SELECT behavior, COUNT(*) as cnt
            FROM user_behavior
            GROUP BY behavior
            ORDER BY cnt DESC
        """).fetchall()
        
        print(f"\n✅ Import completed!")
        print(f"Total rows imported: {total_rows}")
        print("\nBehavior distribution:")
        for behavior, cnt in behavior_stats:
            print(f"  - {behavior}: {cnt}")
        
    except Exception as e:
        print(f"\n❌ Error importing data: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()

