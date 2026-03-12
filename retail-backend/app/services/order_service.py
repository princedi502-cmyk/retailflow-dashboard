from fastapi import HTTPException
from datetime import datetime
from app.db.mongodb import db_manager
from uuid import uuid4


async def create_order_service(order,user:dict):

    product_collection = db_manager.db["products"]
    order_collection = db_manager.db["orders"]
    user_collection = db_manager.db["users"]

    order_items = []
    total_price = 0

    for item in order.items:

        product = await product_collection.find_one({"barcode": item.barcode})

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.barcode} not found"
            )

        if product["stock"] < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for {product['name']}"
            )

        item_total = product["price"] * item.quantity
        total_price += item_total

        order_items.append({
                "product_id": str(product["_id"]),
                "barcode": product["barcode"],
                "name": product["name"],
                "price": product["price"],
                "quantity": item.quantity
                
        })

        await product_collection.update_one(
            {"_id": product["_id"]},
            {"$inc": {"stock": -item.quantity}}
        )

    order_data = {
        "items": order_items,
        "total_price": total_price,
        "user_id": str(user["_id"]),
        "created_at": datetime.utcnow()
    }

    result = await order_collection.insert_one(order_data)

    order_data["id"] = str(result.inserted_id)

    return order_data


async def get_orders_service():

    order_collection = db_manager.db["orders"]

    orders = []

    async for order in order_collection.find():

        order["id"] = str(order["_id"])

        orders.append(order)
    
    return orders