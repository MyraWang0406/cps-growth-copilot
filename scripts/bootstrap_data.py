# scripts/bootstrap_data.py
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Optional, Dict, Any, Set, Tuple, List

import duckdb
from huggingface_hub import hf_hub_download
from tqdm import tqdm

try:
    import orjson  # faster
    def _loads(s: str) -> Dict[str, Any]:
        return orjson.loads(s)
except Exception:
    def _loads(s: str) -> Dict[str, Any]:
        return json.loads(s)


REPO_ID = "McAuley-Lab/Amazon-Reviews-2023"
REPO_TYPE = "dataset"  # ✅ 必须是 dataset

# Category mapping (alias -> actual category name in repo)
CATEGORY_MAPPING = {
    "3c": "Electronics",
    "3C": "Electronics",
    "electronics": "Electronics",
}


def _normalize_category(category: str) -> str:
    category = (category or "").strip()
    return CATEGORY_MAPPING.get(category, category)


def _iter_lines(path: Path) -> Iterable[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line
    else:
        with open(path, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line


_price_re = re.compile(r"(\d+(?:\.\d+)?)")


def _parse_price(v: Any) -> Optional[float]:
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    m = _price_re.search(s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _db_path() -> Path:
    """Get unified DB path (relative to repo root)."""
    repo_root = Path(__file__).resolve().parent.parent
    p = repo_root / "data" / "duckdb" / "cps_growth.duckdb"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("""
    CREATE TABLE IF NOT EXISTS items (
        parent_asin      VARCHAR,
        title            VARCHAR,
        main_category    VARCHAR,
        categories_json  VARCHAR,
        store            VARCHAR,
        price            DOUBLE,
        average_rating   DOUBLE,
        rating_number    BIGINT,
        raw_json         VARCHAR,
        category         VARCHAR
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        parent_asin   VARCHAR,
        user_id       VARCHAR,
        rating        DOUBLE,
        timestamp     BIGINT,
        title         VARCHAR,
        text          VARCHAR,
        raw_json      VARCHAR,
        category      VARCHAR
    );
    """)


def _clear_tables(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DELETE FROM items;")
    con.execute("DELETE FROM reviews;")


def _candidate_filenames_for_category(category: str) -> Tuple[List[str], List[str]]:
    """
    不用 list_repo_files，直接按固定路径尝试：
      raw/meta_categories/meta_{category}.jsonl(.gz)
      raw/review_categories/{category}.jsonl(.gz)
    """
    meta_base = f"raw/meta_categories/meta_{category}.jsonl"
    review_base = f"raw/review_categories/{category}.jsonl"
    meta_candidates = [meta_base, meta_base + ".gz"]
    review_candidates = [review_base, review_base + ".gz"]
    return meta_candidates, review_candidates


def _download_first_existing(
    candidates: List[str],
    cache_dir: Optional[Path],
    file_type: str,
) -> Tuple[Path, str]:
    last_err: Optional[Exception] = None
    for filename in candidates:
        try:
            p = hf_hub_download(
                repo_id=REPO_ID,
                repo_type=REPO_TYPE,
                filename=filename,
                cache_dir=str(cache_dir) if cache_dir else None,
            )
            return Path(p), filename
        except Exception as e:
            last_err = e

    print(f"\n❌ Failed to download {file_type}. Tried:", file=sys.stderr)
    for f in candidates:
        print(f"   - {f}", file=sys.stderr)
    if last_err:
        print(f"\nLast error: {last_err}", file=sys.stderr)
        print(f"\n💡 Tips:", file=sys.stderr)
        print(f"   1) Try login: huggingface-cli login", file=sys.stderr)
        print(f"   2) Or set HF_TOKEN env var", file=sys.stderr)
        print(f"   3) Verify dataset: https://huggingface.co/datasets/{REPO_ID}", file=sys.stderr)
    sys.exit(1)


def _download_raw_files(category: str, cache_dir: Optional[Path]) -> Tuple[Path, Path]:
    meta_candidates, review_candidates = _candidate_filenames_for_category(category)

    print("Downloading meta (try .jsonl then .jsonl.gz):")
    meta_path, meta_name = _download_first_existing(meta_candidates, cache_dir, "meta")
    print(f"✅ meta: {meta_name}")

    print("Downloading reviews (try .jsonl then .jsonl.gz):")
    review_path, review_name = _download_first_existing(review_candidates, cache_dir, "review")
    print(f"✅ review: {review_name}")

    return meta_path, review_path


def _import_meta(
    con: duckdb.DuckDBPyConnection,
    meta_path: Path,
    meta_limit: int,
    category: str
) -> Set[str]:
    keep: Set[str] = set()
    rows = []
    for i, line in enumerate(tqdm(_iter_lines(meta_path), desc=f"Import meta [{category}]")):
        if meta_limit and i >= meta_limit:
            break
        try:
            dp = _loads(line)
        except Exception:
            continue

        parent_asin = dp.get("parent_asin")
        if not parent_asin:
            continue

        parent_asin = str(parent_asin)
        keep.add(parent_asin)

        rows.append((
            parent_asin,
            dp.get("title"),
            dp.get("main_category"),
            json.dumps(dp.get("categories", []), ensure_ascii=False),
            dp.get("store"),
            _parse_price(dp.get("price")),
            float(dp["average_rating"]) if dp.get("average_rating") is not None else None,
            int(dp["rating_number"]) if dp.get("rating_number") is not None else None,
            line,
            category
        ))

    if rows:
        con.executemany("""
            INSERT INTO items(
                parent_asin, title, main_category, categories_json, store,
                price, average_rating, rating_number, raw_json, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)

    return keep


def _import_reviews(
    con: duckdb.DuckDBPyConnection,
    review_path: Path,
    keep_parent_asins: Set[str],
    reviews_limit: int,
    scan_limit: int,
    category: str
) -> None:
    rows = []
    kept = 0

    for i, line in enumerate(tqdm(_iter_lines(review_path), desc=f"Scan reviews [{category}]")):
        if scan_limit and i >= scan_limit:
            break
        if reviews_limit and kept >= reviews_limit:
            break

        try:
            dp = _loads(line)
        except Exception:
            continue

        parent_asin = dp.get("parent_asin") or dp.get("asin")
        if not parent_asin:
            continue

        parent_asin = str(parent_asin)
        if parent_asin not in keep_parent_asins:
            continue

        kept += 1
        rows.append((
            parent_asin,
            dp.get("user_id") or dp.get("reviewerID"),
            float(dp.get("rating") or dp.get("overall")) if (dp.get("rating") or dp.get("overall")) is not None else None,
            int(dp.get("timestamp") or dp.get("unixReviewTime") or 0),
            dp.get("title") or dp.get("reviewTitle"),
            dp.get("text") or dp.get("reviewText"),
            line,
            category
        ))

        if len(rows) >= 2000:
            con.executemany("""
                INSERT INTO reviews(parent_asin, user_id, rating, timestamp, title, text, raw_json, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, rows)
            rows.clear()

    if rows:
        con.executemany("""
            INSERT INTO reviews(parent_asin, user_id, rating, timestamp, title, text, raw_json, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default=None, help="Single category name (e.g., All_Beauty, 3C)")
    ap.add_argument("--categories", type=str, default=None,
                    help="Multiple categories (comma-separated, e.g., All_Beauty,Electronics)")
    ap.add_argument("--meta-limit", type=int, default=5000, help="Limit for meta items per category")
    ap.add_argument("--reviews-limit", type=int, default=20000, help="Limit for reviews per category")
    ap.add_argument("--scan-limit", type=int, default=120000, help="Limit for scanning reviews per category")
    ap.add_argument("--reset", action="store_true", help="Clear tables before import")
    ap.add_argument("--hf-cache-dir", type=str, default="data/hf_cache",
                    help="HuggingFace cache directory (default: data/hf_cache)")
    args = ap.parse_args()

    if args.categories:
        categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    elif args.category:
        categories = [args.category]
    else:
        categories = ["All_Beauty"]

    categories = [_normalize_category(c) for c in categories]
    print(f"📦 Importing categories: {', '.join(categories)}")

    cache_dir = Path(args.hf_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"Using HuggingFace cache: {cache_dir}")

    db_file = _db_path()
    print(f"DB: {db_file}")

    # ✅ 用 with，确保脚本结束自动 close，减少 Windows 锁文件
    with duckdb.connect(str(db_file)) as con:
        _ensure_schema(con)
        if args.reset:
            _clear_tables(con)

        for category in categories:
            print(f"\n{'='*60}")
            print(f"Importing category: {category}")
            print(f"{'='*60}")

            meta_path, review_path = _download_raw_files(category, cache_dir)
            keep = _import_meta(con, meta_path, args.meta_limit, category)
            _import_reviews(con, review_path, keep, args.reviews_limit, args.scan_limit, category)

            cat_items = con.execute("SELECT COUNT(*) FROM items WHERE category = ?", [category]).fetchone()[0]
            cat_reviews = con.execute("SELECT COUNT(*) FROM reviews WHERE category = ?", [category]).fetchone()[0]
            print(f"✅ Category '{category}': {cat_items} items, {cat_reviews} reviews")

        items = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        reviews = con.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        print(f"\n=== Import Summary ===")
        print(f"Total Items: {items}")
        print(f"Total Reviews: {reviews}")

        if items == 0 or reviews == 0:
            print("\n⚠️  Warning: No data imported! Check logs above.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
