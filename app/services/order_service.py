import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.schemas.order import OrderListResponse, OrderResponse, OrderUpsert, Pagination


async def upsert_order(session: AsyncSession, payload: OrderUpsert) -> Order:
    values = {"order_id": payload.order_id, "status": payload.status}
    dialect = session.get_bind().dialect.name
    insert = sqlite_insert if dialect == "sqlite" else postgresql_insert
    statement = insert(Order).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[Order.order_id],
        set_={"status": statement.excluded.status, "updated_at": func.now()},
    ).returning(Order)

    result = await session.execute(statement)
    order = result.scalar_one()
    result.close()
    await session.commit()
    return order


def _apply_filters(
    query: Select,
    start_date: date | None,
    end_date: date | None,
    order_id: uuid.UUID | None,
    order_status: str | None,
) -> Select:
    if start_date:
        query = query.where(
            Order.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        )
    if end_date:
        next_day = datetime.combine(end_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        query = query.where(Order.created_at < next_day)
    if order_id:
        query = query.where(Order.order_id == order_id)
    if order_status:
        query = query.where(Order.status == order_status)
    return query


async def list_orders(
    session: AsyncSession,
    *,
    start_date: date | None,
    end_date: date | None,
    order_id: uuid.UUID | None,
    order_status: str | None,
    page: int,
    limit: int,
) -> OrderListResponse:
    filters = (start_date, end_date, order_id, order_status)
    count_query = _apply_filters(select(func.count(Order.id)), *filters)
    total = (await session.execute(count_query)).scalar_one()

    query = _apply_filters(select(Order), *filters)
    query = query.order_by(Order.created_at.desc(), Order.id.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    orders = (await session.execute(query)).scalars().all()

    return OrderListResponse(
        data=[OrderResponse.model_validate(order) for order in orders],
        pagination=Pagination(
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        ),
    )
