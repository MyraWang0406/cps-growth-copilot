from pathlib import Path
import pandas as pd

SRC = Path("data/raw/tianchi")
out = SRC / "UserBehavior.csv"

user_files = sorted(SRC.glob("tianchi_fresh_comp_train_user*.csv"))
if not user_files:
    raise SystemExit(
        f"[ERR] 没找到 user*.csv：{SRC.resolve()}\n"
        f"你现在有哪些文件：{[p.name for p in SRC.glob('*')]}"
    )

NROWS_EACH = 50000  # 想更小就改 10000；想更大就改 200000；想全量就改 None
KEEP_COLS = ["user_id", "item_id", "behavior_type", "user_geohash", "item_category", "time"]

dfs = []
for f in user_files:
    print("[READ]", f)
    df = pd.read_csv(f, nrows=NROWS_EACH)

    # 关键：干掉类似 Unnamed: 0 这种多余列
    df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed")]

    missing = [c for c in KEEP_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"[ERR] {f.name} 缺列 {missing}; 实际列：{list(df.columns)}")

    df = df[KEEP_COLS]
    dfs.append(df)

df_all = pd.concat(dfs, ignore_index=True)

# 可选：把 1/2/3/4 映射成 pv/fav/cart/buy（你想要“看得懂”的话就开着）
MAP = {1: "pv", 2: "fav", 3: "cart", 4: "buy"}
def _map_behavior(x):
    try:
        xi = int(x)
        return MAP.get(xi, x)
    except Exception:
        return x

df_all["behavior_type"] = df_all["behavior_type"].apply(_map_behavior)

out.parent.mkdir(parents=True, exist_ok=True)
df_all.to_csv(out, index=False, encoding="utf-8")

print("[OK] saved:", out.resolve())
print("[OK] rows :", len(df_all))
print("[OK] sizeMB:", round(out.stat().st_size / 1024 / 1024, 2))
print("[OK] head :", list(df_all.columns))
print("[OK] behavior_type top:", df_all["behavior_type"].value_counts().head(10).to_dict())
