"""
Orders Mock & Operational API Endpoints.
Matches Section 3 of assessment specification.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import OrderResponse, OrderStatusResponse
from app.services.order_service import order_service
from app.repositories.order_repository import OrderRepository
from app.core.exceptions import ServiceUnavailableError, OrderNotFoundError
import json

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.get("", response_model=List[OrderResponse])
async def list_orders(limit: int = 50, db: Session = Depends(get_db)):
    """List recent orders for explorer/dashboard."""
    repo = OrderRepository(db)
    orders = repo.list_all(limit=limit)
    res = []
    for o in orders:
        res.append(OrderResponse(
            id=o.id,
            customer_id=o.customer_id,
            customer_name=o.customer_name,
            status=o.status,
            items=json.loads(o.items_json) if o.items_json else [],
            subtotal=o.subtotal,
            tax=o.tax,
            delivery_fee=o.delivery_fee,
            total=o.total,
            delivery_address=o.delivery_address,
            delivery_partner=o.delivery_partner,
            estimated_delivery_minutes=o.estimated_delivery_minutes,
            payment_status=o.payment_status,
            can_cancel=o.can_cancel,
            created_at=o.created_at,
            updated_at=o.updated_at
        ))
    return res


@router.get("/{orderId}/status")
async def get_order_status(orderId: str):
    """Retrieve current operational status of an order."""
    try:
        result = order_service.get_order_status(orderId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Order not found"))
        return result
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)


@router.get("/{orderId}")
async def get_order_details(orderId: str):
    """Retrieve full itemized order details."""
    try:
        result = order_service.get_order_details(orderId)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Order not found"))
        return result
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
