from __future__ import annotations

import duckdb

DB = r".\data\duckdb\cps_growth.duckdb"
TABLE = "item_funnel_features"

def pick(cols: list[str], *cands: str) -> str | None:
    for c in cands:
        if c in cols:
            return c
    return None

con = duckdb.connect(DB, read_only=True)

cols = [r[1] for r in con.execute(f"pragma table_info('{TABLE}')").fetchall()]
print("[OK] columns:", cols)

item = pick(cols, "item_id", "item", "id")
pv   = pick(cols, "pv", "pv_cnt", "pv_count", "pv_n", "pv_count")
fav  = pick(cols, "fav", "fav_cnt", "fav_count", "fav_n", "fav_count")
cart = pick(cols, "cart", "cart_cnt", "cart_count", "cart_n", "cart_count")
buy  = pick(cols, "buy", "buy_cnt", "buy_count", "buy_n", "buy_count")
rate = pick(cols, "pv_to_buy_rate", "pv_buy_rate", "pv_to_buy")

need = [("item", item), ("pv", pv), ("fav", fav), ("cart", cart), ("buy", buy), ("rate", rate)]
missing = [k for k,v in need if v is None]
if missing:
    raise SystemExit(f"[ERR] missing columns: {missing}")

mx = con.execute(f"select max({rate}) from {TABLE}").fetchone()[0]
print("[OK] max_rate:", mx)

q = f"""
select {item} as item_id, {pv} as pv, {fav} as fav, {cart} as cart, {buy} as buy, {rate} as pv_to_buy_rate
from {TABLE}
order by pv_to_buy_rate desc nulls last, pv desc
limit 10
"""
print("[OK] top10:", con.execute(q).fetchall())
con.close()
