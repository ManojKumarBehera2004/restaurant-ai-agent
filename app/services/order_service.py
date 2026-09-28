"""
Order Business Service.
Coordinates order lookup, status verification, and cancellation policies.
"""

import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.exceptions import OrderNotFoundError, ServiceUnavailableError, AppBaseException
from app.core.security import SecurityGuardrails
from app.models.database import SessionLocal
from app.models.entities import OrderEntity
from app.models.schemas import OrderResponse, OrderStatusResponse, OrderItemSchema


class OrderService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def _get_session(self) -> Session:
        return self.db if self.db else SessionLocal()

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieve authoritative status for an order.
        Simulates outage if SIMULATE_ORDER_SERVICE_OUTAGE is active.
        """
        if settings.SIMULATE_ORDER_SERVICE_OUTAGE:
            raise ServiceUnavailableError("Order Management API (Mock Outage Active)")

        clean_id = SecurityGuardrails.sanitize_order_id(order_id)
        if not clean_id:
            return {"success": False, "error": "Invalid or empty order ID provided."}

        session = self._get_session()
        try:
            order = session.query(OrderEntity).filter(OrderEntity.id == clean_id).first()
            if not order:
                return {
                    "success": False,
                    "error": f"Order '{clean_id}' was not found in the restaurant operational system. Please verify the ID."
                }

            status_messages = {
                "RECEIVED": "Order has been received and is waiting for kitchen confirmation.",
                "PREPARING": "Kitchen is actively preparing your dishes.",
                "OUT_FOR_DELIVERY": f"Your order is out for delivery with {order.delivery_partner or 'courier'}. ETA: {order.estimated_delivery_minutes or 15} minutes.",
                "DELIVERED": "Order was successfully delivered. Enjoy your meal!",
                "CANCELLED": "Order was cancelled. Any charged amount has been refunded.",
                "FAILED": "Order placement encountered a technical failure. Support ticket recommended."
            }

            return {
                "success": True,
                "order_id": order.id,
                "customer_name": order.customer_name,
                "status": order.status,
                "estimated_delivery_minutes": order.estimated_delivery_minutes,
                "delivery_partner": order.delivery_partner,
                "can_cancel": order.can_cancel,
                "message": status_messages.get(order.status, f"Order status is {order.status}."),
                "last_updated": order.updated_at.isoformat() if order.updated_at else None
            }
        finally:
            if not self.db:
                session.close()

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Retrieve complete order breakdown including line items, subtotal, and address.
        """
        if settings.SIMULATE_ORDER_SERVICE_OUTAGE:
            raise ServiceUnavailableError("Order Management API (Mock Outage Active)")

        clean_id = SecurityGuardrails.sanitize_order_id(order_id)
        if not clean_id:
            return {"success": False, "error": "Invalid order ID provided."}

        session = self._get_session()
        try:
            order = session.query(OrderEntity).filter(OrderEntity.id == clean_id).first()
            if not order:
                return {
                    "success": False,
                    "error": f"Order '{clean_id}' does not exist in our records."
                }

            items = json.loads(order.items_json) if order.items_json else []
            return {
                "success": True,
                "order_id": order.id,
                "customer_name": order.customer_name,
                "status": order.status,
                "items": items,
                "subtotal": order.subtotal,
                "tax": order.tax,
                "delivery_fee": order.delivery_fee,
                "total": order.total,
                "delivery_address": order.delivery_address,
                "delivery_partner": order.delivery_partner,
                "payment_status": order.payment_status,
                "can_cancel": order.can_cancel,
                "created_at": order.created_at.isoformat() if order.created_at else None
            }
        finally:
            if not self.db:
                session.close()

    def request_cancellation(self, order_id: str, reason: str = "Customer request") -> Dict[str, Any]:
        """
        Evaluate cancellation business rules:
        - If status == 'RECEIVED' (can_cancel == True): Cancel immediately and refund.
        - If status == 'PREPARING': Food is cooking; reject direct cancellation, suggest ticket.
        - If status == 'OUT_FOR_DELIVERY' or 'DELIVERED': Reject cancellation.
        """
        if settings.SIMULATE_ORDER_SERVICE_OUTAGE:
            raise ServiceUnavailableError("Order Management API (Mock Outage Active)")

        clean_id = SecurityGuardrails.sanitize_order_id(order_id)
        session = self._get_session()
        try:
            order = session.query(OrderEntity).filter(OrderEntity.id == clean_id).first()
            if not order:
                return {"success": False, "error": f"Order '{clean_id}' not found."}

            if order.status == "RECEIVED" and order.can_cancel:
                order.status = "CANCELLED"
                order.payment_status = "REFUNDED"
                order.can_cancel = False
                session.commit()
                return {
                    "success": True,
                    "cancelled": True,
                    "order_id": order.id,
                    "status": "CANCELLED",
                    "refund_status": "REFUNDED",
                    "message": f"Order {order.id} has been successfully cancelled and 100% refund of ${order.total:.2f} has been initiated."
                }
            elif order.status == "PREPARING":
                return {
                    "success": True,
                    "cancelled": False,
                    "order_id": order.id,
                    "status": "PREPARING",
                    "message": f"Order {order.id} is already being prepared by the kitchen and cannot be self-cancelled. A support ticket can be opened if this is an urgent emergency."
                }
            else:
                return {
                    "success": False,
                    "cancelled": False,
                    "order_id": order.id,
                    "status": order.status,
                    "message": f"Order {order.id} cannot be cancelled because its current status is '{order.status}'."
                }
        finally:
            if not self.db:
                session.close()


order_service = OrderService()
