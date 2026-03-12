from pydantic import BaseModel
from typing import List
from datetime import datetime


class OrderItem(BaseModel):
    product_id: str
    name: str
    price: float
    quantity: int


class OrderCreate(BaseModel):
    items: List[OrderItem]


class OrderResponse(BaseModel):
    id: str
    user_id: str  
    items: List[OrderItem]
    total: float
    created_at: datetime