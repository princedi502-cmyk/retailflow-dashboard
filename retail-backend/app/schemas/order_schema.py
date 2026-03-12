from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class OrderItem(BaseModel):
    barcode: Optional[str] = None
    productId: Optional[str] = None
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItem]

class OrderItemResponse(BaseModel):
    product_id: str
    barcode: Optional[str] = None
    name: str
    price: float
    quantity: int


class OrderResponse(BaseModel):
    id: str
    user_id: str  
    items: List[OrderItemResponse]
    total_price: float
    created_at: datetime

    class Config:
        from_attributes = True