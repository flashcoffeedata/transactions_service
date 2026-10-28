import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import verify_api_key
from app.db.database import get_db
from app.schemas.order import OrderListResponse, OrderResponse, OrderUpsert
from app.services.order_service import list_orders, upsert_order

router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=OrderResponse, status_code=200)
async def create_or_update_order(
    payload: OrderUpsert, session: AsyncSession = Depends(get_db)
) -> OrderResponse:
    order = await upsert_order(session, payload)
    return OrderResponse.model_validate(order)


@router.get("", response_model=OrderListResponse)
async def get_orders(
    start_date: date | None = None,
    end_date: date | None = None,
    order_id: uuid.UUID | None = None,
    status: str | None = Query(default=None, min_length=1, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderListResponse:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    if limit > settings.max_page_limit:
        raise HTTPException(
            status_code=422,
            detail=f"limit must be less than or equal to {settings.max_page_limit}",
        )
    return await list_orders(
        session,
        start_date=start_date,
        end_date=end_date,
        order_id=order_id,
        order_status=status,
        page=page,
        limit=limit,
    )
