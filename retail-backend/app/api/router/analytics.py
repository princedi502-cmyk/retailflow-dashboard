from bson import ObjectId
from fastapi import APIRouter, Depends
from app.db.mongodb import db_manager
from app.api.router.dependency import get_current_user, require_employee, require_owner
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/revenue")
async def total_revenue(user=Depends(require_owner)):
    """Total all-time revenue."""
    order_collection = db_manager.db["orders"]

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"}
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(1)

    if result:
        return {"total_revenue": result[0]["total_revenue"]}

    return {"total_revenue": 0}


@router.get("/orders-count")
async def total_orders(user=Depends(get_current_user)):
    order_collection = db_manager.db["orders"]
    count = await order_collection.count_documents({})
    return {"total_orders": count}


@router.get("/top-products")
async def top_products(user=Depends(get_current_user)):
    order_collection = db_manager.db["orders"]

    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.name",
                "total_sold": {"$sum": "$items.quantity"},
                "total_revenue": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.quantity", 0]},
                            {"$ifNull": ["$items.price", 0]}
                        ]
                    }
                }
            }
        },
        {"$sort": {"total_sold": -1}},
        {"$limit": 5},
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "name",
                "as": "product_info"
            }
        },
        {
            "$project": {
                "name": "$_id",
                "unitsSold": "$total_sold",
                "revenue": "$total_revenue",
                "category": {"$ifNull": [{"$arrayElemAt": ["$product_info.category", 0]}, "N/A"]},
                "stock": {"$ifNull": [{"$arrayElemAt": ["$product_info.stock", 0]}, 0]},
                "_id": 0
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(5)
    return result


@router.get("/worst-products")
async def worst_products(user=Depends(get_current_user)):
    order_collection = db_manager.db["orders"]

    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.name",
                "total_sold": {"$sum": "$items.quantity"},
                "total_revenue": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.quantity", 0]},
                            {"$ifNull": ["$items.price", 0]}
                        ]
                    }
                }
            }
        },
        {"$sort": {"total_sold": 1}},
        {"$limit": 5},
        {
            "$lookup": {
                "from": "products",
                "localField": "_id",
                "foreignField": "name",
                "as": "product_info"
            }
        },
        {
            "$project": {
                "name": "$_id",
                "unitsSold": "$total_sold",
                "revenue": "$total_revenue",
                "category": {"$ifNull": [{"$arrayElemAt": ["$product_info.category", 0]}, "N/A"]},
                "stock": {"$ifNull": [{"$arrayElemAt": ["$product_info.stock", 0]}, 0]},
                "_id": 0
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(5)
    return result


@router.get("/sales-summary")
async def sales_summary(user=Depends(get_current_user)):
    """Returns items sold today and this week."""
    order_collection = db_manager.db["orders"]

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    week_start = today_start - timedelta(days=today_start.weekday())

    pipeline = [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "today": {
                    "$sum": {
                        "$cond": [
                            {"$gte": ["$created_at", today_start]},
                            "$items.quantity",
                            0
                        ]
                    }
                },
                "week": {
                    "$sum": {
                        "$cond": [
                            {"$gte": ["$created_at", week_start]},
                            "$items.quantity",
                            0
                        ]
                    }
                }
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(1)

    if result:
        return {
            "items_sold_today": result[0]["today"],
            "items_sold_week": result[0]["week"]
        }

    return {
        "items_sold_today": 0,
        "items_sold_week": 0
    }


@router.get("/low-stock-products")
async def low_stock_products(user=Depends(get_current_user)):
    product_collection = db_manager.db["products"]

    pipeline = [
        {
            "$match": {"stock": {"$lt": 10}}
        },
        {
            "$project": {
                "_id": 0,
                "name": 1,
                "stock": 1,
                "category": {"$ifNull": ["$category", "N/A"]}
            }
        }
    ]

    cursor = product_collection.aggregate(pipeline)
    products = await cursor.to_list(length=50)
    return products


@router.get("/monthly-revenue")
async def monthly_revenue(user=Depends(get_current_user)):
    """Returns array of 12 revenue values indexed by month (0=Jan)."""
    order_collection = db_manager.db["orders"]

    pipeline = [
        {
            "$project": {
                "month": {"$month": {"$toDate": "$created_at"}},
                "total": "$total_price"
            }
        },
        {
            "$group": {
                "_id": "$month",
                "revenue": {"$sum": "$total"}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    result = await order_collection.aggregate(pipeline).to_list(length=100)

    months_revenue = [0] * 12

    for item in result:
        if item["_id"] is not None:
            month_index = item["_id"] - 1
            months_revenue[month_index] = item["revenue"]

    return {"values": months_revenue}


@router.get("/category-sales")
async def category_sales(user=Depends(get_current_user)):
    """
    FIX: Was grouping by $category and summing $total — neither exists on orders.
    Now unwinds items, looks up product for category, and multiplies qty * price.
    """
    order_collection = db_manager.db["orders"]

    pipeline = [
        {"$unwind": "$items"},
        {
            "$lookup": {
                "from": "products",
                "localField": "items.name",
                "foreignField": "name",
                "as": "product_info"
            }
        },
        {
            "$group": {
                "_id": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$product_info.category", 0]},
                        "Uncategorized"
                    ]
                },
                "revenue": {
                    "$sum": {
                        "$multiply": [
                            {"$ifNull": ["$items.quantity", 0]},
                            {"$ifNull": ["$items.price", 0]}
                        ]
                    }
                }
            }
        },
        {"$sort": {"revenue": -1}}
    ]

    result = await order_collection.aggregate(pipeline).to_list(length=None)

    labels = [r["_id"] for r in result]
    values = [r["revenue"] for r in result]

    return {"labels": labels, "values": values}


@router.get("/items-sold")
async def items_sold(user=Depends(get_current_user)):
    """Items sold in the current calendar month."""
    sales_collection = db_manager.db["orders"]

    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": start}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "itemsSold": {"$sum": {"$ifNull": ["$items.quantity", 0]}}
            }
        }
    ]

    result = await sales_collection.aggregate(pipeline).to_list(1)
    return {"itemsSold": result[0]["itemsSold"] if result else 0}


@router.get("/this-month")
async def this_month(user=Depends(get_current_user)):
    """
    FIX: Was incomplete/missing. Returns this month's revenue and items sold.
    This is the single endpoint the dashboard KPI cards should use.
    """
    order_collection = db_manager.db["orders"]

    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    pipeline = [
        {
            "$match": {
                "created_at": {"$gte": month_start}
            }
        },
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$total_price"},
                "items_sold": {"$sum": {"$ifNull": ["$items.quantity", 0]}}
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(1)

    if result:
        return {
            "total_revenue": result[0]["total_revenue"],
            "items_sold": result[0]["items_sold"]
        }

    return {
        "total_revenue": 0,
        "items_sold": 0
    }

@router.get("/sales-by-employee")
async def sales_by_employee(user=Depends(require_owner)):
    order_collection = db_manager.db["orders"]
    user_collection = db_manager.db["users"]
    pipeline = [
    # 1. Group BEFORE unwind to count orders correctly
    {
        "$group": {
            "_id": "$user_id",
            "total_revenue": {"$sum": "$total_price"},
            "order_count": {"$sum": 1},           # count orders here before unwind
            "all_items": {"$push": "$items"}       # collect all items arrays
        }
    },

    # 2. Unwind the collected items arrays
    {"$unwind": "$all_items"},
    {"$unwind": "$all_items"},                     # double unwind needed: first unwraps outer array, second unwraps inner items

    # 3. Now sum quantities correctly
    {
        "$group": {
            "_id": "$_id",
            "total_revenue": {"$first": "$total_revenue"},
            "order_count": {"$first": "$order_count"},
            "items_sold": {"$sum": "$all_items.quantity"}
        }
    },

    # 4. Convert string user_id to ObjectId for lookup
    {
        "$addFields": {
            "user_object_id": {"$toObjectId": "$_id"}
        }
    },

    # 5. Join with users collection
    {
        "$lookup": {
            "from": "users",
            "localField": "user_object_id",
            "foreignField": "_id",
            "as": "user_info"
        }
    },

    {"$unwind": "$user_info"},

    # 6. Final output shape
    {
        "$project": {
            "_id": 0,
            "user_id": "$_id",
            "username": "$user_info.username",
            "email": "$user_info.email",
            "total_revenue": 1,
            "order_count": 1,
            "items_sold": 1
        }
    },

    {"$sort": {"total_revenue": -1}}
]

    result = await order_collection.aggregate(pipeline).to_list(None)
    return result

@router.get("/top-product")
async def get_top_product(user= Depends(require_owner)):
    order_collection = db_manager.db["orders"]
    product_collection = db_manager.db["products"]

    pipeline = [
        {"$unwind": "$items"},
        { 
           "$group":{
                "_id": "$items.product_id",
                "item_sold":{"$sum":"$items.quantity"},
                "total_revenue": {
                    "$sum": {
                        "$multiply": ["$items.price","$items.quantity"]
                    }
                },
                "order_count": {"$sum": 1},           # count orders here before unwind
            }
        },
        
        {
            "$addFields": {
                "product_object_id": {"$toObjectId": "$_id"}
            }
        },
        {
            "$lookup": {
                "from": "products",
                "localField": "product_object_id",
                "foreignField": "_id",
                "as": "product_info"
            }
        },
        {"$unwind": "$product_info"},

        {
            "$project": {
                "_id": 0,
                "product_id": "$_id",
                "product_name": "$product_info.name",
                "barcode": "$product_info.barcode",
                "total_revenue": 1,
                "order_count": 1,
                "items_sold": 1
            }
        },

        {"$sort": {"total_revenue": -1}}
    ]
    result = await order_collection.aggregate(pipeline).to_list(1)
    return result


@router.get("/unsold-products")
async def unsold_products(user =Depends(require_owner)):
    product_collection = db_manager.db["products"]

    days_ago = datetime.now(timezone.utc) - timedelta(days=1)

    pipeline = [
        {
            "$lookup":{
                "from": "orders",
                "let":{"product_id":{"$toString":"$_id"}},
                "pipeline":[
                    {"$unwind":"$items"},
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq":["$items.product_id","$$product_id"]},
                                    {"gte":["$created_at",days_ago]}
                                ]
                            }
                        }
                    }
                ],
                "as": "recent_orders"
            }
        },

        {
            "$match":{
                "recent_orders":{"$size":0}
            }
        },
        {
            "$project":{
                "_id": 0,
                "product_id":{"$toString":"$_id"},
                "name":1,
                "barcode":1,
                "price":1,
                "stock":1,
                "category":1,

            }
        }
    ]

    result = await product_collection.aggregate(pipeline).to_list(None)
    return result

















    # pipeline = [
    #     {
    #         "$match":{
    #             "user_id" {"$user_id": ObjectId(user_id)}
    #         }
    #     },
    #     {"$unwind": "$items"},
    #             {
    #         "$group": {
    #             "user_id": ObjectId(user_id),
    #             "total_revenue": {"$sum": "$total_price"},
    #             "items_sold": {"$sum": {"$ifNull": ["$items.quantity", 0]}}
    #         }
    #     }
    # ]

#     pipeline = [
#     {
#         "$group": {
#             "_id": "$user_id",               
#             "total_revenue": {"$sum": "$total_price"}, 
#             "order_count": {"$sum": 1},      
#             "item_list": {"$push": "$items"},
#             "items_sold": {"$sum": {"$ifNull": ["$items.quantity", 0]}},
#         }
#     },
#     {
#         "$sort": {"total_revenue": -1}        
#     }
# ]
#     result = await order_collection.aggregate(pipeline).to_list(1)

#     if result:
#         return {
#             "_id":result[0]["_id"],
#             "total_revenue": result[0]["total_revenue"],
#             "items_sold": result[0]["items_sold"]
#         }

#     return {
#         "total_revenue": 0,
#         "items_sold": 0
#     }