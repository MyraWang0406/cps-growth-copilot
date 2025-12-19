"""Alerts endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from datetime import date, timedelta
from ..db import get_db
from ..models import Order, Click
from ..schemas import AlertsResponse, Alert
from datetime import datetime

router = APIRouter()


@router.post("/alerts/run", response_model=AlertsResponse)
async def run_alerts(db: AsyncSession = Depends(get_db)):
    """Run alert detection."""
    alerts = []
    today = date.today()
    last_7d = today - timedelta(days=7)
    last_14d = today - timedelta(days=14)

    # Check CVR drop
    # Compare last 7d vs previous 7d
    cvr_7d_query = select(
        Order.taoke_id,
        func.count(Order.id).label("orders"),
        func.count(Click.id).label("clicks"),
    ).join(
        Click, Order.click_id == Click.id, isouter=True
    ).where(
        and_(
            func.date(Order.ordered_at) >= last_7d,
            func.date(Order.ordered_at) < today,
        )
    ).group_by(Order.taoke_id)

    cvr_7d_result = await db.execute(cvr_7d_query)
    cvr_7d_data = cvr_7d_result.all()

    for row in cvr_7d_data:
        if row.clicks > 100:  # Only alert if significant volume
            cvr = (row.orders / row.clicks * 100) if row.clicks > 0 else 0
            if cvr < 1.0:  # Threshold
                alerts.append(Alert(
                    type="cvr_drop",
                    severity="warning",
                    title=f"淘客 {row.taoke_id} 转化率偏低",
                    description=f"过去 7 天 CVR 为 {cvr:.2f}%，低于 1% 阈值",
                    entity_id=row.taoke_id,
                    entity_type="taoke",
                    detected_at=datetime.now(),
                    evidence=[{
                        "metric": "CVR",
                        "value": f"{cvr:.2f}%",
                        "comparison": "阈值 1%",
                        "time_window": "7d",
                    }],
                ))

    # Check refund spike
    refund_query = select(
        Order.merchant_id,
        func.count(Order.id).label("total_orders"),
        func.sum(case((Order.status == "refunded", 1), else_=0)).label("refunds"),
    ).where(
        and_(
            func.date(Order.ordered_at) >= last_7d,
            func.date(Order.ordered_at) < today,
        )
    ).group_by(Order.merchant_id)

    refund_result = await db.execute(refund_query)
    refund_data = refund_result.all()

    for row in refund_data:
        if row.total_orders > 10:  # Only alert if significant volume
            refund_rate = (row.refunds / row.total_orders * 100) if row.total_orders > 0 else 0
            if refund_rate > 15.0:  # Threshold
                alerts.append(Alert(
                    type="refund_spike",
                    severity="critical",
                    title=f"商家 {row.merchant_id} 退款率异常",
                    description=f"过去 7 天退款率为 {refund_rate:.2f}%，超过 15% 阈值",
                    entity_id=row.merchant_id,
                    entity_type="merchant",
                    detected_at=datetime.now(),
                    evidence=[{
                        "metric": "退款率",
                        "value": f"{refund_rate:.2f}%",
                        "comparison": "阈值 15%",
                        "time_window": "7d",
                    }],
                ))

    return AlertsResponse(alerts=alerts, total=len(alerts))

