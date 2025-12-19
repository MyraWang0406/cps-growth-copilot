import argparse
from pathlib import Path
import duckdb


def project_root() -> Path:
    # .../app/api/scripts/rebuild_user_behavior_duckdb.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=str, default=str(project_root() / "data" / "raw" / "tianchi" / "UserBehavior.csv"))
    p.add_argument("--db", type=str, default=str(project_root() / "data" / "duckdb" / "cps_growth.duckdb"))
    p.add_argument("--limit", type=int, default=0, help="0 表示不限制；>0 表示只导入前 N 行")
    args = p.parse_args()

    csv_path = Path(args.csv)
    db_path = Path(args.db)

    if not csv_path.exists():
        raise SystemExit(f"[ERR] CSV not found: {csv_path.resolve()}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    try:
        print("[OK] DB:", db_path.resolve())
        print("[OK] CSV:", csv_path.resolve())

        con.execute("DROP TABLE IF EXISTS user_behavior")

        limit_sql = f"LIMIT {args.limit}" if args.limit and args.limit > 0 else ""

        # 统一产出列：user_id, item_id, behavior_type(pv/fav/cart/buy), user_geohash, item_category, timestamp
        con.execute(
            f"""
            CREATE TABLE user_behavior AS
            SELECT
              try_cast(user_id AS BIGINT) AS user_id,
              try_cast(item_id AS BIGINT) AS item_id,
              CASE
                WHEN lower(cast(behavior_type AS VARCHAR)) IN ('pv','fav','cart','buy')
                  THEN lower(cast(behavior_type AS VARCHAR))
                WHEN try_cast(behavior_type AS INTEGER) = 1 THEN 'pv'
                WHEN try_cast(behavior_type AS INTEGER) = 2 THEN 'fav'
                WHEN try_cast(behavior_type AS INTEGER) = 3 THEN 'cart'
                WHEN try_cast(behavior_type AS INTEGER) = 4 THEN 'buy'
                ELSE lower(cast(behavior_type AS VARCHAR))
              END AS behavior_type,
              nullif(cast(user_geohash AS VARCHAR), '') AS user_geohash,
              try_cast(item_category AS INTEGER) AS item_category,
              COALESCE(
                try_cast(time AS TIMESTAMP),
                try_strptime(cast(time AS VARCHAR), '%Y-%m-%d %H'),
                try_strptime(cast(time AS VARCHAR), '%Y-%m-%d %H:%M:%S')
              ) AS timestamp
            FROM read_csv_auto(?, header=true, sample_size=-1)
            {limit_sql}
            """,
            [str(csv_path)],
        )

        total = con.execute("SELECT count(*) FROM user_behavior").fetchone()[0]
        cols = [r[1] for r in con.execute("PRAGMA table_info('user_behavior')").fetchall()]
        dist = con.execute("SELECT behavior_type, count(*) c FROM user_behavior GROUP BY 1 ORDER BY c DESC").fetchall()

        print("[OK] user_behavior rows:", total)
        print("[OK] columns:", cols)
        print("[OK] behavior dist:", dist[:10])

    finally:
        con.close()


if __name__ == "__main__":
    main()
