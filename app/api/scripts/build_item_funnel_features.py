# app/api/scripts/build_item_funnel_features.py
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

import duckdb


def _pick_col(existing: Sequence[str], candidates: Iterable[str]) -> Optional[str]:
    lower_map = {c.lower(): c for c in existing}
    for cand in candidates:
        key = cand.lower()
        if key in lower_map:
            return lower_map[key]
    return None


def _require_col(existing: Sequence[str], candidates: Iterable[str], human_name: str) -> str:
    col = _pick_col(existing, candidates)
    if not col:
        raise RuntimeError(
            f"找不到 {human_name} 列。候选列名={list(candidates)}，实际表列={list(existing)}"
        )
    return col


def build_item_funnel_features(
    con: duckdb.DuckDBPyConnection,
    source_table: str,
    user_col: str,
    item_col: str,
    action_col: str,
    ts_col: str,
    mode: str,
) -> None:
    """
    产出：item 维度漏斗特征（去重用户口径）
    - loose：只要求下游行为发生在 pv 之后（>= pv_ts）
    - strict：要求 pv_ts < fav_ts < cart_ts < buy_ts（真正漏斗顺序）
    输出表/视图：
      - item_funnel_features_loose
      - item_funnel_features_strict（如 mode 包含 strict）
      - item_funnel_features / item_funnel_features_default -> loose（兼容旧代码）
      - item_funnel_features_both（可选：带 strict 标记）
    """

    # 1) 规范化行为表（统一成 user_id/item_id/action/ts）
    con.execute("DROP VIEW IF EXISTS ub_norm")
    con.execute(
        f"""
        CREATE TEMP VIEW ub_norm AS
        SELECT
          CAST({user_col} AS BIGINT) AS user_id,
          CAST({item_col} AS BIGINT) AS item_id,

          -- ✅ 关键：兼容 Tianchi 的 behavior_type=1/2/3/4
          CASE
            WHEN TRY_CAST({action_col} AS INTEGER) IS NOT NULL THEN
              CASE TRY_CAST({action_col} AS INTEGER)
                WHEN 1 THEN 'pv'
                WHEN 2 THEN 'fav'
                WHEN 3 THEN 'cart'
                WHEN 4 THEN 'buy'
                ELSE NULL
              END
            ELSE
              LOWER(CAST({action_col} AS VARCHAR))
          END AS action,

          -- ✅ ts 兼容：数字/字符串数字/时间戳
          CASE
            WHEN TRY_CAST({ts_col} AS BIGINT) IS NOT NULL THEN TRY_CAST({ts_col} AS BIGINT)
            ELSE CAST(EPOCH(CAST({ts_col} AS TIMESTAMP)) AS BIGINT)
          END AS ts

        FROM {source_table}
        WHERE {user_col} IS NOT NULL
          AND {item_col} IS NOT NULL
          AND {action_col} IS NOT NULL
          AND {ts_col} IS NOT NULL
        """
    )

    # 2) 每个 user-item 取四个行为的“最早时间”（去重到同一用户同一商品）
    con.execute("DROP TABLE IF EXISTS user_item_stage")
    con.execute(
        """
        CREATE TEMP TABLE user_item_stage AS
        SELECT
          user_id,
          item_id,
          MIN(CASE WHEN action='pv'   THEN ts END) AS pv_ts,
          MIN(CASE WHEN action='fav'  THEN ts END) AS fav_ts,
          MIN(CASE WHEN action='cart' THEN ts END) AS cart_ts,
          MIN(CASE WHEN action='buy'  THEN ts END) AS buy_ts
        FROM ub_norm
        WHERE action IN ('pv','fav','cart','buy')
          AND ts IS NOT NULL
        GROUP BY user_id, item_id
        """
    )

    def _select_sql(strict: int) -> str:
        """
        strict=0（loose）：只要求 fav/cart/buy 发生在 pv 之后（>= pv_ts）
        strict=1（strict）：要求 pv_ts < fav_ts < cart_ts < buy_ts
        """
        if strict == 0:
            fav_ok = "pv_ts IS NOT NULL AND fav_ts  IS NOT NULL AND fav_ts  >= pv_ts"
            cart_ok = "pv_ts IS NOT NULL AND cart_ts IS NOT NULL AND cart_ts >= pv_ts"
            buy_ok = "pv_ts IS NOT NULL AND buy_ts  IS NOT NULL AND buy_ts  >= pv_ts"
            fav_cart_ok = "fav_ts IS NOT NULL AND cart_ts IS NOT NULL AND cart_ts >= fav_ts"
            cart_buy_ok = "cart_ts IS NOT NULL AND buy_ts IS NOT NULL AND buy_ts >= cart_ts"
        else:
            fav_ok = "pv_ts IS NOT NULL AND fav_ts  IS NOT NULL AND fav_ts  >  pv_ts"
            cart_ok = (
                "pv_ts IS NOT NULL AND fav_ts IS NOT NULL AND cart_ts IS NOT NULL "
                "AND fav_ts > pv_ts AND cart_ts > fav_ts"
            )
            buy_ok = (
                "pv_ts IS NOT NULL AND fav_ts IS NOT NULL AND cart_ts IS NOT NULL AND buy_ts IS NOT NULL "
                "AND fav_ts > pv_ts AND cart_ts > fav_ts AND buy_ts > cart_ts"
            )
            fav_cart_ok = "fav_ts IS NOT NULL AND cart_ts IS NOT NULL AND cart_ts > fav_ts"
            cart_buy_ok = "cart_ts IS NOT NULL AND buy_ts IS NOT NULL AND buy_ts > cart_ts"

        return f"""
        SELECT
          item_id,

          -- ✅ 这里的 pv/fav/cart/buy 是“去重用户数口径”（每 user-item 最多记 1）
          SUM(CASE WHEN pv_ts IS NOT NULL THEN 1 ELSE 0 END) AS pv,
          SUM(CASE WHEN {fav_ok}  THEN 1 ELSE 0 END)         AS fav,
          SUM(CASE WHEN {cart_ok} THEN 1 ELSE 0 END)         AS cart,
          SUM(CASE WHEN {buy_ok}  THEN 1 ELSE 0 END)         AS buy,

          -- 兼容旧字段命名（避免后端/前端列名不一致）
          SUM(CASE WHEN pv_ts IS NOT NULL THEN 1 ELSE 0 END) AS pv_count,
          SUM(CASE WHEN {fav_ok}  THEN 1 ELSE 0 END)         AS fav_count,
          SUM(CASE WHEN {cart_ok} THEN 1 ELSE 0 END)         AS cart_count,
          SUM(CASE WHEN {buy_ok}  THEN 1 ELSE 0 END)         AS buy_count,

          CAST(SUM(CASE WHEN {fav_ok}  THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(SUM(CASE WHEN pv_ts IS NOT NULL THEN 1 ELSE 0 END),0) AS pv_to_fav_rate,
          CAST(SUM(CASE WHEN {cart_ok} THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(SUM(CASE WHEN pv_ts IS NOT NULL THEN 1 ELSE 0 END),0) AS pv_to_cart_rate,
          CAST(SUM(CASE WHEN {buy_ok}  THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(SUM(CASE WHEN pv_ts IS NOT NULL THEN 1 ELSE 0 END),0) AS pv_to_buy_rate,

          CAST(SUM(CASE WHEN {fav_cart_ok} THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(SUM(CASE WHEN {fav_ok} THEN 1 ELSE 0 END),0)      AS fav_to_cart_rate,
          CAST(SUM(CASE WHEN {cart_buy_ok} THEN 1 ELSE 0 END) AS DOUBLE) / NULLIF(SUM(CASE WHEN {cart_ok} THEN 1 ELSE 0 END),0)     AS cart_to_buy_rate

        FROM user_item_stage
        GROUP BY item_id
        """

    # 3) 落表：loose / strict
    if mode in ("both", "nonstrict"):
        con.execute("DROP TABLE IF EXISTS item_funnel_features_loose")
        con.execute(f"CREATE TABLE item_funnel_features_loose AS {_select_sql(0)}")

    if mode in ("both", "strict"):
        con.execute("DROP TABLE IF EXISTS item_funnel_features_strict")
        con.execute(f"CREATE TABLE item_funnel_features_strict AS {_select_sql(1)}")

    # 4) 兼容视图：旧代码就读 item_funnel_features / default
    con.execute("DROP VIEW IF EXISTS item_funnel_features")
    con.execute("DROP VIEW IF EXISTS item_funnel_features_default")
    con.execute(
        """
        CREATE VIEW item_funnel_features AS
        SELECT * FROM item_funnel_features_loose
        """
    )
    con.execute(
        """
        CREATE VIEW item_funnel_features_default AS
        SELECT * FROM item_funnel_features_loose
        """
    )

    # 5) 可选：两套口径合并（带 strict 标记）
    con.execute("DROP VIEW IF EXISTS item_funnel_features_both")
    if mode == "both":
        con.execute(
            """
            CREATE VIEW item_funnel_features_both AS
            SELECT 0 AS strict, * FROM item_funnel_features_loose
            UNION ALL
            SELECT 1 AS strict, * FROM item_funnel_features_strict
            """
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-path", required=True, help=r"DuckDB 文件路径，如 .\data\duckdb\cps_growth.duckdb")
    ap.add_argument("--source-table", default="user_behavior", help="行为表表名（默认 user_behavior）")
    ap.add_argument("--mode", default="both", choices=["both", "nonstrict", "strict"], help="生成口径：both/非严格/严格")

    ap.add_argument("--user-col", default="", help="用户列名（可选）")
    ap.add_argument("--item-col", default="", help="商品列名（可选）")
    ap.add_argument("--action-col", default="", help="行为列名（可选）")
    ap.add_argument("--ts-col", default="", help="时间戳列名（可选）")

    args = ap.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"[ERROR] DuckDB 不存在：{db_path}", file=sys.stderr)
        return 2

    con = duckdb.connect(str(db_path))

    try:
        info = con.execute(f"PRAGMA table_info('{args.source_table}')").fetchall()
        cols = [r[1] for r in info]
    except Exception as e:
        print(f"[ERROR] 读取源表失败：{args.source_table}；{e}", file=sys.stderr)
        print("你可以用：SHOW TABLES；确认行为表到底叫什么（user_behavior / userbehavior / UserBehavior 等）", file=sys.stderr)
        return 3

    user_col = args.user_col or _require_col(cols, ["user_id", "userid", "uid", "user"], "user_id")
    item_col = args.item_col or _require_col(cols, ["item_id", "itemid", "iid", "item"], "item_id")
    action_col = args.action_col or _require_col(cols, ["behavior_type", "behavior", "action", "event_type", "type"], "behavior/action")
    ts_col = args.ts_col or _require_col(cols, ["ts", "timestamp", "time", "event_time"], "timestamp")

    print("[INFO] source_table =", args.source_table)
    print("[INFO] mapped cols   =", {"user": user_col, "item": item_col, "action": action_col, "ts": ts_col})
    print("[INFO] mode         =", args.mode)

    build_item_funnel_features(
        con=con,
        source_table=args.source_table,
        user_col=user_col,
        item_col=item_col,
        action_col=action_col,
        ts_col=ts_col,
        mode=args.mode,
    )

    # 快速校验：转化率不会再出现 500% 这种（理论上都 <= 1）
    top10 = con.execute(
        """
        SELECT item_id, pv, fav, cart, buy, pv_to_buy_rate
        FROM item_funnel_features
        ORDER BY pv_to_buy_rate DESC NULLS LAST, pv DESC
        LIMIT 10
        """
    ).fetchall()

    bad = con.execute(
        """
        SELECT
          SUM(CASE WHEN pv_to_buy_rate > 1.00001 THEN 1 ELSE 0 END) AS bad_rate_rows,
          MAX(pv_to_buy_rate) AS max_rate
        FROM item_funnel_features
        """
    ).fetchone()

    print("[OK] top10 (loose/default):")
    for r in top10:
        print("   ", r)
    print("[OK] rate_check =", bad)

    return 0
    # con.close() 放 finally 里

    # noqa: E999


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        # 防止异常时连接泄漏
        try:
            duckdb.default_connection.close()  # type: ignore[attr-defined]
        except Exception:
            pass
