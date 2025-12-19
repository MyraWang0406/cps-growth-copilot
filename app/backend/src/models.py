"""Database models."""
from sqlalchemy import Column, Integer, String, Decimal, Date, DateTime, ForeignKey, Text, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .db import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Taoke(Base):
    __tablename__ = "taokes"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    name = Column(String(255), nullable=False)
    price = Column(Decimal(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    category = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    name = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, server_default=func.now())


class CommissionRule(Base):
    __tablename__ = "commission_rules"

    id = Column(Integer, primary_key=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    taoke_id = Column(Integer, ForeignKey("taokes.id"), nullable=True)
    commission_rate = Column(Decimal(5, 4), nullable=False)
    commission_type = Column(String(50), default="percentage")
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Content(Base):
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True)
    taoke_id = Column(Integer, ForeignKey("taokes.id"))
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    title = Column(String(500))
    content_type = Column(String(50))
    url = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ContentProductMap(Base):
    __tablename__ = "content_product_map"

    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("contents.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    created_at = Column(DateTime, server_default=func.now())


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True)
    taoke_id = Column(Integer, ForeignKey("taokes.id"))
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    clicked_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(50))
    user_agent = Column(Text)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    taoke_id = Column(Integer, ForeignKey("taokes.id"))
    merchant_id = Column(Integer, ForeignKey("merchants.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    click_id = Column(Integer, ForeignKey("clicks.id"), nullable=True)
    order_amount = Column(Decimal(10, 2), nullable=False)
    commission_amount = Column(Decimal(10, 2), nullable=False)
    status = Column(String(50), default="pending")
    ordered_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

