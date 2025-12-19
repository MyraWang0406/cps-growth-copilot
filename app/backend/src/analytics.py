"""Analytics and metrics calculation functions."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Order, Click, Content, Product, Merchant, Taoke


def parse_window(window: str) -> tuple[date, date]:
    """Parse window string (7d, 14d, 30d) to date range."""
    today = date.today()
    days = int(window.rstrip("d"))
    start_date = today - timedelta(days=days)
    return start_date, today


async def get_taoke_metrics(
    session: AsyncSession, taoke_id: int, window: str
) -> dict:
    """Calculate metrics for a taoke."""
    start_date, end_date = parse_window(window)

    # Clicks
    clicks_query = select(func.count(Click.id)).where(
        and_(
            Click.taoke_id == taoke_id,
            func.date(Click.clicked_at) >= start_date,
            func.date(Click.clicked_at) <= end_date,
        )
    )
    clicks_result = await session.execute(clicks_query)
    clicks = clicks_result.scalar() or 0

    # Impressions (contents)
    impressions_query = select(func.count(Content.id)).where(
        and_(
            Content.taoke_id == taoke_id,
            func.date(Content.created_at) >= start_date,
            func.date(Content.created_at) <= end_date,
        )
    )
    impressions_result = await session.execute(impressions_query)
    impressions = impressions_result.scalar() or 0

    # Orders
    orders_query = select(func.count(Order.id)).where(
        and_(
            Order.taoke_id == taoke_id,
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    orders_result = await session.execute(orders_query)
    orders = orders_result.scalar() or 0

    # Refunds
    refunds_query = select(func.count(Order.id)).where(
        and_(
            Order.taoke_id == taoke_id,
            Order.status == "refunded",
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    refunds_result = await session.execute(refunds_query)
    refunds = refunds_result.scalar() or 0

    # GMV and Commission
    gmv_query = select(
        func.sum(
            case(
                (Order.status.in_(["paid", "pending"]), Order.order_amount),
                else_=0,
            )
        ),
        func.sum(
            case(
                (Order.status.in_(["paid", "pending"]), Order.commission_amount),
                else_=0,
            )
        ),
    ).where(
        and_(
            Order.taoke_id == taoke_id,
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    gmv_result = await session.execute(gmv_query)
    gmv_row = gmv_result.first()
    gmv = Decimal(str(gmv_row[0] or 0))
    commission_paid = Decimal(str(gmv_row[1] or 0))

    # Calculate rates
    ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
    cvr = (orders / clicks * 100) if clicks > 0 else 0.0
    epc = (gmv / clicks) if clicks > 0 else Decimal("0.00")
    refund_rate = (refunds / orders * 100) if orders > 0 else 0.0
    commission_rate = (commission_paid / gmv * 100) if gmv > 0 else 0.0

    return {
        "window": window,
        "start_date": start_date,
        "end_date": end_date,
        "impressions": impressions,
        "clicks": clicks,
        "orders": orders,
        "refunds": refunds,
        "gmv": gmv,
        "commission_paid": commission_paid,
        "ctr": round(ctr, 2),
        "cvr": round(cvr, 2),
        "epc": epc,
        "refund_rate": round(refund_rate, 2),
        "commission_rate": round(commission_rate, 2),
    }


async def get_merchant_metrics(
    session: AsyncSession, merchant_id: int, window: str
) -> dict:
    """Calculate metrics for a merchant."""
    start_date, end_date = parse_window(window)

    # Orders
    orders_query = select(func.count(Order.id)).where(
        and_(
            Order.merchant_id == merchant_id,
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    orders_result = await session.execute(orders_query)
    orders = orders_result.scalar() or 0

    # Refunds
    refunds_query = select(func.count(Order.id)).where(
        and_(
            Order.merchant_id == merchant_id,
            Order.status == "refunded",
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    refunds_result = await session.execute(refunds_query)
    refunds = refunds_result.scalar() or 0

    # GMV and Commission
    gmv_query = select(
        func.sum(
            case(
                (Order.status.in_(["paid", "pending"]), Order.order_amount),
                else_=0,
            )
        ),
        func.sum(
            case(
                (Order.status.in_(["paid", "pending"]), Order.commission_amount),
                else_=0,
            )
        ),
    ).where(
        and_(
            Order.merchant_id == merchant_id,
            func.date(Order.ordered_at) >= start_date,
            func.date(Order.ordered_at) <= end_date,
        )
    )
    gmv_result = await session.execute(gmv_query)
    gmv_row = gmv_result.first()
    gmv = Decimal(str(gmv_row[0] or 0))
    commission_paid = Decimal(str(gmv_row[1] or 0))

    # Clicks (from orders)
    clicks_query = select(func.count(Click.id)).where(
        and_(
            Click.merchant_id == merchant_id,
            func.date(Click.clicked_at) >= start_date,
            func.date(Click.clicked_at) <= end_date,
        )
    )
    clicks_result = await session.execute(clicks_query)
    clicks = clicks_result.scalar() or 0

    # Calculate rates
    cvr = (orders / clicks * 100) if clicks > 0 else 0.0
    epc = (gmv / clicks) if clicks > 0 else Decimal("0.00")
    refund_rate = (refunds / orders * 100) if orders > 0 else 0.0
    commission_rate = (commission_paid / gmv * 100) if gmv > 0 else 0.0

    return {
        "window": window,
        "start_date": start_date,
        "end_date": end_date,
        "impressions": 0,  # Not tracked for merchant
        "clicks": clicks,
        "orders": orders,
        "refunds": refunds,
        "gmv": gmv,
        "commission_paid": commission_paid,
        "ctr": 0.0,  # Not applicable
        "cvr": round(cvr, 2),
        "epc": epc,
        "refund_rate": round(refund_rate, 2),
        "commission_rate": round(commission_rate, 2),
    }

