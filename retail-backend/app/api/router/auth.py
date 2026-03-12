from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.schemas.user_schema import UserCreate, UserResponse
from app.db.mongodb import db_manager
from app.core.security import hashed_password, verify_password, create_access_token


router = APIRouter(prefix="/auth", tags=["auth"])      

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate):

    existing_user = await db_manager.db["users"].find_one(
        {"email": user_in.email}
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user_dict = user_in.model_dump()

    raw_password = user_dict.pop("password")

    user_dict["hashed_password"] = hashed_password(raw_password)

    result = await db_manager.db["users"].insert_one(user_dict)

    return {
        "id": str(result.inserted_id),
        "username": user_dict["username"],
        "email": user_dict["email"],
        "role": user_dict.get("role", "employee")
    }


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):

    user = await db_manager.db["users"].find_one(
    {"email": form_data.username}
)

    if not user or not verify_password(
        form_data.password,
        user["hashed_password"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(
    data={
        "sub": str(user["_id"]),
        "email":user["email"],
        "role": user.get("role")
    }
)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }