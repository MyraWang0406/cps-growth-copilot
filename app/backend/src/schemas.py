"""Pydantic schemas for API requests and responses."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


# Metrics Schemas
class MetricsResponse(BaseModel):
    window: str
    start_date: date
    end_date: date
    impressions: int = 0
    clicks: int = 0
    orders: int = 0
    refunds: int = 0
    gmv: Decimal = Decimal("0.00")
    commission_paid: Decimal = Decimal("0.00")
    ctr: float = 0.0
    cvr: float = 0.0
    epc: Decimal = Decimal("0.00")
    refund_rate: float = 0.0
    commission_rate: float = 0.0


# Diagnosis Schemas
class Evidence(BaseModel):
    metric: str
    value: str
    comparison: Optional[str] = None
    time_window: str


class Insight(BaseModel):
    type: str  # opportunity, risk, trend
    title: str
    description: str
    evidence: List[Evidence]
    impact: str  # high, medium, low


class DiagnosisReport(BaseModel):
    entity_id: int
    entity_type: str  # taoke or merchant
    window: str
    generated_at: datetime
    summary: str
    insights: List[Insight]
    risks: List[Insight]
    next_actions: List[str]


# Opportunities Schemas
class Opportunity(BaseModel):
    id: str
    title: str
    description: str
    impact: str  # high, medium, low
    effort: str  # high, medium, low
    estimated_gain: Optional[str] = None
    evidence: List[Evidence]
    action_items: List[str]


class OpportunitiesResponse(BaseModel):
    entity_id: int
    entity_type: str
    window: str
    opportunities: List[Opportunity]


# Alerts Schemas
class Alert(BaseModel):
    type: str  # cvr_drop, refund_spike, price_change, stock_out, commission_change
    severity: str  # critical, warning, info
    title: str
    description: str
    entity_id: int
    entity_type: str
    detected_at: datetime
    evidence: List[Evidence]


class AlertsResponse(BaseModel):
    alerts: List[Alert]
    total: int

