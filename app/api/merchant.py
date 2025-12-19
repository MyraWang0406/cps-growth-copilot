# app/api/merchant.py
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import io
import csv

router = APIRouter(prefix="/merchant", tags=["merchant"])

try:
    import duckdb  # type: ignore
except ModuleNotFoundError:
    duckdb = None


# -------------------------
# Paths / Connection
# -------------------------
def _repo_root() -> Path:
    # app/api/merchant.py -> parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def _db_path() -> str:
    return str(_repo_root() / "data" / "duckdb" / "cps_growth.duckdb")


def _db_file() -> str:
    return Path(_db_path()).name


def _connect(read_only: bool = True):
    if duckdb is None:
        return None
    return duckdb.connect(_db_path(), read_only=read_only)


def _tables(con) -> List[str]:
    return [r[0] for r in con.execute("show tables").fetchall()]


def _table_cols(con, table: str) -> List[str]:
    # (cid, name, type, notnull, dflt_value, pk)
    return [r[1] for r in con.execute(f"pragma table_info('{table}')").fetchall()]


def _pick(cols: List[str], *cands: str) -> Optional[str]:
    for c in cands:
        if c in cols:
            return c
    return None


def _ts_expr(ts_col: str) -> str:
    # 兼容 timestamp 是 TIMESTAMP 或 string(如 '2014-12-12 12')
    return (
        f"coalesce("
        f"try_cast(\"{ts_col}\" as TIMESTAMP), "
        f"try_strptime(cast(\"{ts_col}\" as varchar), '%Y-%m-%d %H'), "
        f"try_strptime(cast(\"{ts_col}\" as varchar), '%Y-%m-%d %H:%M:%S'), "
        f"try_strptime(cast(\"{ts_col}\" as varchar), '%Y-%m-%d')"
        f")"
    )


def _buy_pred(behavior_col: str) -> str:
    # 兼容 behavior 是 'buy' 或 4 或 '4'
    return f"(lower(cast(\"{behavior_col}\" as varchar))='buy' OR cast(\"{behavior_col}\" as varchar)='4')"


# -------------------------
# Overview
# -------------------------
def _overview_payload() -> Dict[str, Any]:
    db = _db_path()
    if duckdb is None:
        return {"error": "python 环境里没有 duckdb：python -m pip install duckdb"}

    con = duckdb.connect(db, read_only=True)
    try:
        tabs = _tables(con)
        if "user_behavior" not in set(tabs):
            return {"error": "table user_behavior not found", "tables": sorted(tabs)}

        cols = _table_cols(con, "user_behavior")
        user_col = _pick(cols, "user_id", "user")
        item_col = _pick(cols, "item_id", "item")
        behavior_col = _pick(cols, "behavior_type", "behavior")
        ts_col = _pick(cols, "timestamp", "time", "ts")

        total = int(con.execute("select count(*) from user_behavior").fetchone()[0])
        users = int(con.execute(f'select count(distinct "{user_col}") from user_behavior').fetchone()[0]) if user_col else None
        items = int(con.execute(f'select count(distinct "{item_col}") from user_behavior').fetchone()[0]) if item_col else None

        by_type_norm: Dict[str, int] = {"pv": 0, "fav": 0, "cart": 0, "buy": 0}
        if behavior_col:
            raw = con.execute(f'select "{behavior_col}" as k, count(*) c from user_behavior group by 1').fetchall()
            m = {"1": "pv", "2": "fav", "3": "cart", "4": "buy", "pv": "pv", "fav": "fav", "cart": "cart", "buy": "buy"}
            for k, c in raw:
                ks = str(k).strip().lower()
                kk = m.get(ks)
                if kk:
                    by_type_norm[kk] += int(c)

        funnel_rows = 0
        if "item_funnel_features" in set(tabs):
            funnel_rows = int(con.execute("select count(*) from item_funnel_features").fetchone()[0])

        # Amazon cache 仅提示存在性（不暴露本机路径）
        amazon_cache_ok = (_repo_root() / "data" / "hf_cache").exists()

        return {
            "db_file": _db_file(),  # debug 用，前端不要展示
            "tables": sorted(tabs),
            "user_behavior_rows": total,
            "distinct_users": users,
            "distinct_items": items,
            "behavior_counts": by_type_norm,
            "item_funnel_features_rows": funnel_rows,
            "detected_cols": {
                "user_col": user_col,
                "item_col": item_col,
                "behavior_col": behavior_col,
                "timestamp_col": ts_col,
            },
            "columns": cols,  # debug 用，前端不要展示
            "sources": {
                "tianchi": "阿里天池开源数据（UserBehavior / Fresh 赛）",
                "amazon": "Amazon 开源（Beauty 已缓存）" if amazon_cache_ok else "Amazon 开源（可选接入）",
                "derived": "行为数据衍生（选品特征）",
            },
        }
    finally:
        con.close()


# -------------------------
# Metrics (D1 retention / 7d repurchase)
# -------------------------
def _metrics_payload() -> Dict[str, Any]:
    if duckdb is None:
        return {"error": "duckdb not installed"}

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        tabs = set(_tables(con))
        if "user_behavior" not in tabs:
            return {"error": "table user_behavior not found"}

        cols = _table_cols(con, "user_behavior")
        user_col = _pick(cols, "user_id", "user")
        behavior_col = _pick(cols, "behavior_type", "behavior")
        ts_col = _pick(cols, "timestamp", "time", "ts")
        if not user_col or not ts_col:
            return {"error": "缺 user_id 或 timestamp/time 列"}

        ts = _ts_expr(ts_col)

        # D1 retention：取“最新且存在 next day 的那天”
        d1 = con.execute(
            f"""
            with day_users as (
              select date({ts}) as d, "{user_col}" as uid
              from user_behavior
              where {ts} is not null
              group by 1,2
            ),
            ret as (
              select a.d as d,
                     count(*) as active_users,
                     sum(case when b.uid is null then 0 else 1 end) as retained_users
              from day_users a
              left join day_users b
                on b.uid=a.uid and b.d = a.d + interval 1 day
              group by 1
            )
            select d, active_users, retained_users,
                   retained_users::double / nullif(active_users,0) as rate
            from ret
            where d < (select max(d) from ret)
            order by d desc
            limit 1
            """
        ).fetchone()

        d1_payload = None
        if d1:
            d1_payload = {
                "day": str(d1[0]),
                "active_users": int(d1[1]),
                "retained_users": int(d1[2]),
                "rate": float(d1[3]) if d1[3] is not None else None,
            }

        rep_payload = None
        if behavior_col:
            buy_pred = _buy_pred(behavior_col)
            rep = con.execute(
                f"""
                with buys as (
                  select "{user_col}" as uid, {ts} as ts
                  from user_behavior
                  where {ts} is not null and {buy_pred}
                ),
                first_buy as (
                  select uid, min(ts) as first_ts
                  from buys
                  group by 1
                ),
                agg as (
                  select
                    count(*) as buyers,
                    sum(case when exists (
                      select 1 from buys b2
                      where b2.uid = fb.uid
                        and b2.ts > fb.first_ts
                        and b2.ts <= fb.first_ts + interval 7 day
                    ) then 1 else 0 end) as repurchasers
                  from first_buy fb
                )
                select buyers, repurchasers,
                       repurchasers::double / nullif(buyers,0) as rate
                from agg
                """
            ).fetchone()
            if rep:
                rep_payload = {
                    "buyers": int(rep[0]),
                    "repurchasers_7d": int(rep[1]),
                    "rate": float(rep[2]) if rep[2] is not None else None,
                }

        membership_payload = {
            "available": False,
            "note": "Demo 使用天池开源行为数据：无会员字段/订单 GMV。后续接会员/订单表补齐。",
        }

        return {
            "db_file": _db_file(),  # debug 用，前端不要展示
            "d1_retention": d1_payload,
            "repurchase_7d": rep_payload,
            "membership": membership_payload,
        }
    finally:
        con.close()


# -------------------------
# Lifecycle segments
# -------------------------
_SEG_RULES_ZH = {
    "new": "新客：first_day == anchor_day（首次出现即锚点日）",
    "active": "活跃：last_day==anchor_day 且 近7天活跃天数>=3",
    "warm": "回访：last_day < anchor_day 且 last_day>=anchor_day-7天",
    "dormant": "沉睡：last_day < anchor_day-7天 且 last_day>=anchor_day-30天",
}
_SEG_ZH = {"new": "新客", "active": "活跃", "warm": "回访", "dormant": "沉睡"}


def _segments_payload() -> Dict[str, Any]:
    if duckdb is None:
        return {"error": "duckdb not installed"}

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        tabs = set(_tables(con))
        if "user_behavior" not in tabs:
            return {"error": "table user_behavior not found"}

        cols = _table_cols(con, "user_behavior")
        user_col = _pick(cols, "user_id", "user")
        ts_col = _pick(cols, "timestamp", "time", "ts")
        if not user_col or not ts_col:
            return {"error": "缺 user_id 或 timestamp/time 列"}

        ts = _ts_expr(ts_col)

        q = f"""
        with e as (
          select "{user_col}" as u, date({ts}) as d
          from user_behavior
          where {ts} is not null
          group by 1,2
        ),
        anchor as (select max(d) as anchor_day from e),
        agg as (
          select
            u,
            min(d) as first_day,
            max(d) as last_day,
            sum(case when d >= (select anchor_day from anchor) - interval 7 day then 1 else 0 end) as days_7d,
            count(*) as active_days_30d
          from e
          where d >= (select anchor_day from anchor) - interval 30 day
          group by u
        ),
        seg as (
          select
            u,
            case
              when first_day = (select anchor_day from anchor) then 'new'
              when last_day = (select anchor_day from anchor) and days_7d >= 3 then 'active'
              when last_day < (select anchor_day from anchor) and last_day >= (select anchor_day from anchor) - interval 7 day then 'warm'
              when last_day < (select anchor_day from anchor) - interval 7 day and last_day >= (select anchor_day from anchor) - interval 30 day then 'dormant'
              else 'dormant'
            end as segment,
            active_days_30d
          from agg
        ),
        stat as (
          select segment, count(*) as users, avg(active_days_30d) as avg_actions
          from seg
          group by segment
        ),
        tot as (select sum(users) as total_users from stat)
        select
          (select anchor_day from anchor) as anchor_day,
          segment, users,
          users::double / nullif((select total_users from tot),0) as share,
          avg_actions
        from stat
        order by users desc
        """

        rows = con.execute(q).fetchall()
        if not rows:
            return {"anchor_day": None, "total_users": 0, "segments": [], "defs": {"zh": _SEG_ZH, "rules": _SEG_RULES_ZH}}

        anchor_day = str(rows[0][0])
        segs: List[Dict[str, Any]] = []
        total_users = 0
        for _, seg, users, share, avg_actions in rows:
            total_users += int(users or 0)
            segs.append(
                {
                    "segment": seg,
                    "segment_zh": _SEG_ZH.get(seg, seg),
                    "rule_zh": _SEG_RULES_ZH.get(seg, ""),
                    "users": int(users or 0),
                    "share": float(share) if share is not None else 0.0,
                    "avg_actions": float(avg_actions) if avg_actions is not None else 0.0,
                }
            )

        return {
            "anchor_day": anchor_day,
            "total_users": total_users,
            "segments": segs,
            "defs": {"zh": _SEG_ZH, "rules": _SEG_RULES_ZH},
        }
    finally:
        con.close()


# -------------------------
# Items top (from item_funnel_features)
# -------------------------
def _items_top_payload(limit: int = 20, min_pv: int = 0) -> Dict[str, Any]:
    if duckdb is None:
        return {"items": [], "error": "duckdb not installed"}

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        tabs = set(_tables(con))
        if "item_funnel_features" not in tabs:
            return {"items": [], "note": "未生成 item_funnel_features：先运行 build_item_funnel_features.py"}

        cols = _table_cols(con, "item_funnel_features")
        item_col = _pick(cols, "item_id", "item", "id")
        pv_col = _pick(cols, "pv", "pv_cnt", "pv_count", "pv_n")
        fav_col = _pick(cols, "fav", "fav_cnt", "fav_count", "fav_n")
        cart_col = _pick(cols, "cart", "cart_cnt", "cart_count", "cart_n")
        buy_col = _pick(cols, "buy", "buy_cnt", "buy_count", "buy_n")
        rate_col = _pick(cols, "pv_to_buy_rate", "pv_to_buy", "pv_buy_rate")

        if not item_col or not pv_col or not buy_col:
            return {"items": [], "error": f"item_funnel_features 列不全：{cols}"}

        sel_rate = f"\"{rate_col}\"" if rate_col else f"(\"{buy_col}\"::double / nullif(\"{pv_col}\",0))"
        where = f"where \"{pv_col}\" >= {int(min_pv)}" if min_pv > 0 else ""
        q = f"""
        select
          "{item_col}" as item_id,
          "{pv_col}" as pv,
          {f"\"{fav_col}\" as fav," if fav_col else "0 as fav,"}
          {f"\"{cart_col}\" as cart," if cart_col else "0 as cart,"}
          "{buy_col}" as buy,
          {sel_rate} as pv_to_buy_rate
        from item_funnel_features
        {where}
        order by pv_to_buy_rate desc nulls last, pv desc
        limit {int(limit)}
        """
        rows = con.execute(q).fetchall()
        items = [
            {
                "item_id": r[0],
                "pv": int(r[1] or 0),
                "fav": int(r[2] or 0),
                "cart": int(r[3] or 0),
                "buy": int(r[4] or 0),
                "pv_to_buy_rate": float(r[5]) if r[5] is not None else 0.0,
            }
            for r in rows
        ]
        return {"items": items, "sort": "pv_to_buy_rate", "min_pv": int(min_pv)}
    finally:
        con.close()


# -------------------------
# Items opportunity (high PV, low conversion)
# -------------------------
def _items_opportunity_payload(limit: int = 20, min_pv: int = 50) -> Dict[str, Any]:
    if duckdb is None:
        return {"items": [], "error": "duckdb not installed"}

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        tabs = set(_tables(con))
        if "item_funnel_features" not in tabs:
            return {"items": [], "note": "未生成 item_funnel_features"}

        cols = _table_cols(con, "item_funnel_features")
        item_col = _pick(cols, "item_id", "item", "id")
        pv_col = _pick(cols, "pv", "pv_cnt", "pv_count", "pv_n")
        fav_col = _pick(cols, "fav", "fav_cnt", "fav_count", "fav_n")
        cart_col = _pick(cols, "cart", "cart_cnt", "cart_count", "cart_n")
        buy_col = _pick(cols, "buy", "buy_cnt", "buy_count", "buy_n")
        rate_col = _pick(cols, "pv_to_buy_rate", "pv_to_buy", "pv_buy_rate")

        if not item_col or not pv_col or not buy_col:
            return {"items": [], "error": f"item_funnel_features 列不全：{cols}"}

        sel_rate = f"\"{rate_col}\"" if rate_col else f"(\"{buy_col}\"::double / nullif(\"{pv_col}\",0))"
        q = f"""
        select
          "{item_col}" as item_id,
          "{pv_col}" as pv,
          {f"\"{fav_col}\" as fav," if fav_col else "0 as fav,"}
          {f"\"{cart_col}\" as cart," if cart_col else "0 as cart,"}
          "{buy_col}" as buy,
          {sel_rate} as pv_to_buy_rate
        from item_funnel_features
        where "{pv_col}" >= {int(min_pv)}
        order by pv desc, pv_to_buy_rate asc nulls last
        limit {int(limit)}
        """
        rows = con.execute(q).fetchall()
        items = [
            {
                "item_id": r[0],
                "pv": int(r[1] or 0),
                "fav": int(r[2] or 0),
                "cart": int(r[3] or 0),
                "buy": int(r[4] or 0),
                "pv_to_buy_rate": float(r[5]) if r[5] is not None else 0.0,
            }
            for r in rows
        ]
        return {"items": items, "min_pv": int(min_pv), "sort": "pv desc & low conversion"}
    finally:
        con.close()


# -------------------------
# Advice (Journey/Lifecycle)
# -------------------------
def _journey_advice(behavior_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    pv = int(behavior_counts.get("pv", 0) or 0)
    fav = int(behavior_counts.get("fav", 0) or 0)
    cart = int(behavior_counts.get("cart", 0) or 0)
    buy = int(behavior_counts.get("buy", 0) or 0)

    def _rate(a: int, b: int) -> float:
        return (b / a) if a > 0 else 0.0

    pv_fav = _rate(pv, fav)
    fav_cart = _rate(fav, cart)
    cart_buy = _rate(cart, buy)

    return [
        {
            "key": "pv_fav",
            "title": "浏览→收藏偏低",
            "tag": "建议：提升兴趣",
            "detail": "收藏意向弱：用内容场景/对比卖点/达人讲解强化“为什么需要它”，并在详情页增加信任背书与权益提醒。",
            "metric": {"from": "pv", "to": "fav", "rate": pv_fav},
            "default_segment": "warm",
            "default_message_type": "pv_low_fav",
        },
        {
            "key": "fav_cart",
            "title": "收藏→加购需要推动",
            "tag": "建议：促转",
            "detail": "收藏后未加购：用限时券/套装/包邮门槛，配合“对比清单/搭配建议”把用户推到加购。",
            "metric": {"from": "fav", "to": "cart", "rate": fav_cart},
            "default_segment": "warm",
            "default_message_type": "fav_drop",
        },
        {
            "key": "cart_buy",
            "title": "加购→购买转化尚可（优先做放大）",
            "tag": "建议：放大",
            "detail": "对高意向人群做“套装/加价购/阶梯满减”，提升客单；对加购未买做 24h 内触达（券/包邮/评价露出/对比内容）。",
            "metric": {"from": "cart", "to": "buy", "rate": cart_buy},
            "default_segment": "warm",
            "default_message_type": "cart_drop",
        },
    ]


def _lifecycle_advice(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    adv: List[Dict[str, Any]] = []
    d1 = (metrics.get("d1_retention") or {}) if metrics else {}
    rep = (metrics.get("repurchase_7d") or {}) if metrics else {}

    d1_rate = d1.get("rate")
    if d1_rate is None:
        adv.append(
            {
                "key": "d1_unknown",
                "title": "次日留存：待计算",
                "tag": "建议：排查",
                "detail": "先确保 user_behavior 导入成功且 timestamp 可解析。",
                "default_segment": "new",
                "default_message_type": "retention_push",
            }
        )
    elif float(d1_rate) < 0.15:
        adv.append(
            {
                "key": "d1_low",
                "title": "次日留存偏低",
                "tag": "建议：召回",
                "detail": "对昨日有行为但今日未回访：24h 内券/上新/加购提醒，分层触达。",
                "default_segment": "warm",
                "default_message_type": "retention_push",
            }
        )
    else:
        adv.append(
            {
                "key": "d1_ok",
                "title": "次日留存健康",
                "tag": "建议：放大",
                "detail": "把高留存人群做分层：加购&收藏优先触达，推同类新品 + 低门槛权益。",
                "default_segment": "active",
                "default_message_type": "retention_push",
            }
        )

    rep_rate = rep.get("rate")
    if rep_rate is None:
        adv.append(
            {
                "key": "rep_unknown",
                "title": "7日复购：待计算",
                "tag": "建议：补口径",
                "detail": "确保 behavior 可识别 buy（值为 buy 或 4）。",
                "default_segment": "active",
                "default_message_type": "repurchase_push",
            }
        )
    elif float(rep_rate) < 0.08:
        adv.append(
            {
                "key": "rep_low",
                "title": "7日复购偏低",
                "tag": "建议：复购",
                "detail": "首购后 3/5/7 天分批触达：复购券 + 组合装/订阅/周期购。",
                "default_segment": "warm",
                "default_message_type": "repurchase_push",
            }
        )
    else:
        adv.append(
            {
                "key": "rep_ok",
                "title": "7日复购不错",
                "tag": "建议：拉升客单",
                "detail": "把复购人群做高客单包：组合购、阶梯满减、订阅/周期购。",
                "default_segment": "active",
                "default_message_type": "repurchase_push",
            }
        )

    adv.append(
        {
            "key": "member_placeholder",
            "title": "会员运营（占位）",
            "tag": "建议：分层",
            "detail": "Demo 无会员字段；后续接会员/订单表后补“渗透/贡献/拉新转正/沉睡唤醒”。",
            "default_segment": "dormant",
            "default_message_type": "dormant_wakeup",
        }
    )
    return adv


# -------------------------
# Actions API
# -------------------------
def _segment_sql(segment: str) -> Tuple[str, str, str, str]:
    seg = (segment or "").strip().lower()
    if seg not in _SEG_ZH:
        seg = "warm"
    seg_zh = _SEG_ZH[seg]
    rule_zh = _SEG_RULES_ZH[seg]

    if duckdb is None:
        return seg, seg_zh, rule_zh, ""

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        tabs = set(_tables(con))
        if "user_behavior" not in tabs:
            return seg, seg_zh, rule_zh, ""

        cols = _table_cols(con, "user_behavior")
        user_col = _pick(cols, "user_id", "user")
        ts_col = _pick(cols, "timestamp", "time", "ts")
        if not user_col or not ts_col:
            return seg, seg_zh, rule_zh, ""

        ts = _ts_expr(ts_col)

        sql = f"""
with e as (
  select "{user_col}" as u, date({ts}) as d
  from user_behavior
  where {ts} is not null
  group by 1,2
),
anchor as (select max(d) as anchor_day from e),
agg as (
  select
    u,
    min(d) as first_day,
    max(d) as last_day,
    sum(case when d >= (select anchor_day from anchor) - interval 7 day then 1 else 0 end) as days_7d
  from e
  where d >= (select anchor_day from anchor) - interval 30 day
  group by u
),
seg as (
  select
    u,
    case
      when first_day = (select anchor_day from anchor) then 'new'
      when last_day = (select anchor_day from anchor) and days_7d >= 3 then 'active'
      when last_day < (select anchor_day from anchor) and last_day >= (select anchor_day from anchor) - interval 7 day then 'warm'
      when last_day < (select anchor_day from anchor) - interval 7 day and last_day >= (select anchor_day from anchor) - interval 30 day then 'dormant'
      else 'dormant'
    end as segment
  from agg
)
select u as user_id
from seg
where segment = '{seg}'
"""
        return seg, seg_zh, rule_zh + "（anchor_day=max(date(timestamp))）", sql.strip()
    finally:
        con.close()


def _message_template(t: str) -> Dict[str, Any]:
    tp = (t or "").strip().lower()
    templates: Dict[str, Dict[str, Any]] = {
        "cart_drop": {
            "title": "加购未购召回（24h）",
            "channels": ["站内信", "短信", "微信服务通知（如有）"],
            "variables": ["user_name", "item_name", "coupon", "deadline", "link"],
            "copy": {
                "short": "你加购的「{{item_name}}」还没下单～{{coupon}}（{{deadline}}前有效）点击直达：{{link}}",
                "long": "Hi {{user_name}}，你之前加购的「{{item_name}}」还没下单～我们给你准备了{{coupon}}，{{deadline}}前可用。点这里直接购买：{{link}}",
            },
        },
        "fav_drop": {
            "title": "收藏后促转（48h）",
            "channels": ["站内信", "短信"],
            "variables": ["item_name", "benefit", "link"],
            "copy": {
                "short": "你收藏的「{{item_name}}」今天有{{benefit}}，点这里：{{link}}",
                "long": "你收藏的「{{item_name}}」已经为你保留，今天有{{benefit}}。现在下单更划算：{{link}}",
            },
        },
        "pv_low_fav": {
            "title": "浏览高但收藏低（内容种草）",
            "channels": ["站内信", "内容/短视频脚本（达人）"],
            "variables": ["scene", "item_name"],
            "copy": {
                "short": "为什么大家会收藏「{{item_name}}」：{{scene}}场景一用就懂",
                "long": "收藏代表“想要”。建议用{{scene}}场景讲清楚「{{item_name}}」的关键卖点，再补 1-2 个对比点，收藏率会明显提升。",
            },
        },
        "retention_push": {
            "title": "次日留存召回",
            "channels": ["站内信", "短信"],
            "variables": ["benefit", "link"],
            "copy": {
                "short": "今天给你准备了{{benefit}}，点这里看看：{{link}}",
                "long": "昨天你看过的内容今天更新了，我们也给你准备了{{benefit}}：{{link}}",
            },
        },
        "repurchase_push": {
            "title": "首购后 7 日复购推动",
            "channels": ["站内信", "短信"],
            "variables": ["bundle", "coupon", "deadline", "link"],
            "copy": {
                "short": "复购更划算：{{bundle}} + {{coupon}}（{{deadline}}前）{{link}}",
                "long": "给你配好了复购组合：{{bundle}}，再叠加{{coupon}}，{{deadline}}前有效：{{link}}",
            },
        },
        "dormant_wakeup": {
            "title": "沉睡唤醒（强利益点）",
            "channels": ["短信", "站内信"],
            "variables": ["coupon", "deadline", "link"],
            "copy": {
                "short": "好久不见～送你{{coupon}}（{{deadline}}前有效）{{link}}",
                "long": "很久没来啦～这次给你一张{{coupon}}，{{deadline}}前有效，点这里直接用：{{link}}",
            },
        },
    }
    return templates.get(tp, templates["cart_drop"])


@router.get("/actions/segment_sql")
def action_segment_sql(segment: str = "warm"):
    if duckdb is None:
        return JSONResponse({"error": "duckdb not installed"}, status_code=500)
    seg, seg_zh, rule_zh, sql = _segment_sql(segment)
    if not sql:
        return JSONResponse({"error": "segment sql unavailable (missing table/columns?)"}, status_code=500)
    return {"segment": seg, "segment_zh": seg_zh, "rule_zh": rule_zh, "sql": sql}


@router.get("/actions/message_template")
def action_message_template(type: str = "cart_drop"):
    return {"type": type, "template": _message_template(type), "note": "Demo 仅产出模板；后续对接触达系统可一键下发。"}


@router.get("/actions/export_users")
def action_export_users(segment: str = "warm", limit: int = 20000):
    if duckdb is None:
        return JSONResponse({"error": "duckdb not installed"}, status_code=500)

    seg, _, _, sql = _segment_sql(segment)
    if not sql:
        return JSONResponse({"error": "segment sql unavailable (missing table/columns?)"}, status_code=500)

    limit = max(1, min(int(limit), 200000))
    sql2 = sql + f"\nlimit {limit}\n"

    con = duckdb.connect(_db_path(), read_only=True)
    try:
        rows = con.execute(sql2).fetchall()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["user_id"])
        for r in rows:
            w.writerow([r[0]])
        data = buf.getvalue().encode("utf-8")

        filename = f"users_{seg}.csv"
        return StreamingResponse(
            io.BytesIO(data),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        con.close()


# -------------------------
# Public API
# -------------------------
@router.get("/overview")
def overview():
    return _overview_payload()


@router.get("/metrics")
def metrics():
    return _metrics_payload()


@router.get("/dashboard")
def dashboard(items_limit: int = 20, min_pv: int = 0):
    ov = _overview_payload()
    mt = _metrics_payload()
    lc = _segments_payload()

    top = _items_top_payload(limit=items_limit, min_pv=min_pv)
    opp = _items_opportunity_payload(limit=items_limit, min_pv=max(50, min_pv))

    advice = {
        "journey": _journey_advice(ov.get("behavior_counts", {}) if isinstance(ov, dict) else {}),
        "lifecycle": _lifecycle_advice(mt if isinstance(mt, dict) else {}),
    }

    return {
        "overview": ov,
        "metrics": mt,
        "lifecycle": {"segments": lc},
        "items": {"top": top, "opportunity": opp},
        "advice": advice,
    }
