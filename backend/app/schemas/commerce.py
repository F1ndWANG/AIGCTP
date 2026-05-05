from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


# ===== Category =====
class CategoryCreateRequest(BaseModel):
    name: str
    description: str = ""
    icon: str = ""
    sort_order: int = 0
    parent_id: Optional[int] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    description: str = ""
    icon: str = ""
    sort_order: int = 0
    children: Optional[list["CategoryResponse"]] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ===== Product =====
class ProductRequest(BaseModel):
    name: str
    description: str = ""
    price: float
    original_price: Optional[float] = None
    category_id: Optional[int] = None
    image_urls: list[str] = []
    stock: int = 0
    unit: str = "件"
    specs: list[dict[str, Any]] = []
    tags: list[str] = []
    rating: float = 0.0
    status: str = "active"


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str = ""
    price: float
    original_price: Optional[float] = None
    category_id: Optional[int] = None
    image_urls: list[str] = []
    stock: int = 0
    unit: str = "件"
    specs: list[dict[str, Any]] = []
    tags: list[str] = []
    rating: float = 0.0
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    id: int
    name: str
    price: float
    original_price: Optional[float] = None
    image_urls: list[str] = []
    stock: int = 0
    unit: str = "件"
    rating: float = 0.0
    status: str = "active"

    model_config = {"from_attributes": True}


# ===== Cart =====
class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str = ""
    product_image: str = ""
    price: float = 0.0
    unit: str = ""
    quantity: int = 1
    specs: dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse] = []
    total_amount: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddCartItemRequest(BaseModel):
    product_id: int
    quantity: int = 1
    specs: dict[str, Any] = {}


class UpdateCartItemRequest(BaseModel):
    quantity: int


# ===== Order =====
class CreateOrderRequest(BaseModel):
    shipping_address: str = ""
    contact_phone: str = ""
    notes: str = ""


class OrderItemResponse(BaseModel):
    product_id: int
    name: str
    price: float
    quantity: int
    specs: dict[str, Any] = {}
    image_url: str = ""


class OrderResponse(BaseModel):
    id: int
    status: str = "pending"
    total_amount: float = 0.0
    items: list[OrderItemResponse] = []
    shipping_address: str = ""
    contact_phone: str = ""
    notes: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderListItem(BaseModel):
    id: int
    status: str
    total_amount: float = 0.0
    item_count: int = 0
    first_item_name: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}
