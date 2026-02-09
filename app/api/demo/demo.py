from fastapi import APIRouter, Depends
from typing import Union
from pydantic import BaseModel
from app.middleware.jwt import jwt_auth_dependency  # 正确导入依赖
import asyncio


router = APIRouter()

@router.get("/")
def read_root():
    return {"Hello": "World"}

@router.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@router.put("/items/{item_id}")
async def update_item(item_id: int, item: Item, _: None = Depends(jwt_auth_dependency)):
    await asyncio.sleep(2)
    return {"item_name": item.name, "item_id": item_id}