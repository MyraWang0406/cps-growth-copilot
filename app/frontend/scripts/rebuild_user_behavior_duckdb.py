import duckdb

DB = r"data/duckdb/cps_growth.duckdb"
CSV = r"data/raw/tianchi/UserBehavior.csv"

con = duckdb.connect(DB)
con.execute("""
CREATE OR REPLACE TABLE user_behavior AS
SELECT
  CAST(user_id AS BIGINT) AS user_id,
  CAST(item_id AS BIGINT) AS item_id,
  CAST(behavior_type AS VARCHAR) AS behavior_type,
  CAST(user_geohash AS VARCHAR) AS user_geohash,
  CAST(item_category AS BIGINT) AS item_category,
  try_strptime(CAST(time AS VARCHAR), '%Y-%m-%d %H') AS timestamp
FROM read_csv_auto(?, header=true);
""", [CSV])

rows = con.execute("select count(*) from user_behavior").fetchone()[0]
print("[OK] user_behavior rows =", rows)
print("[OK] schema =", con.execute("PRAGMA table_info('user_behavior')").fetchall())
con.close()
