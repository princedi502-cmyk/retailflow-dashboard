from fastapi import APIRouter, Depends
from app.schemas.order_schema import OrderCreate, OrderResponse
from app.api.router.dependency import get_current_user, require_employee, require_owner
from app.services.order_service import create_order_service, get_orders_service

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

@router.post("/", response_model=OrderResponse)
async def create_order(order: OrderCreate, current_user:dict=Depends(get_current_user)):

    return await create_order_service(order,current_user)


@router.get("/", response_model=list[OrderResponse])
async def get_orders(user=Depends(get_current_user)):

    return await get_orders_service()