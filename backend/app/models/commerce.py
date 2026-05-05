from datetime import datetime, timezone
from sqlalchemy import Column, Index, Integer, String, DateTime, JSON, ForeignKey, Float, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(String(500), default="")
    icon = Column(String(200), default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    children = relationship("Category", backref="parent", remote_side=[id], lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    image_urls = Column(JSON, default=list)
    stock = Column(Integer, default=0)
    unit = Column(String(20), default="件")
    specs = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    rating = Column(Float, default=0.0)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    category = relationship("Category", lazy="selectin")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan", lazy="selectin")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity = Column(Integer, default=1)
    specs = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product", lazy="selectin")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_status", "user_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default="pending", index=True)
    total_amount = Column(Float, nullable=False, default=0.0)
    items = Column(JSON, nullable=False, default=list)
    shipping_address = Column(String(500), default="")
    contact_phone = Column(String(20), default="")
    notes = Column(String(500), default="")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="orders")
