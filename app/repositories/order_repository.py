"""
Order Repository.
Encapsulates database access for restaurant orders.
"""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.entities import OrderEntity
from app.core.exceptions import OrderNotFoundError


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: str) -> Optional[OrderEntity]:
        """Fetch an order entity by ID."""
        return self.db.query(OrderEntity).filter(OrderEntity.id == order_id).first()

    def get_by_id_or_raise(self, order_id: str) -> OrderEntity:
        """Fetch order by ID or raise OrderNotFoundError."""
        order = self.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(order_id)
        return order

    def list_all(self, limit: int = 50) -> List[OrderEntity]:
        """List recent orders."""
        return self.db.query(OrderEntity).order_by(OrderEntity.created_at.desc()).limit(limit).all()

    def list_by_customer(self, customer_id: str) -> List[OrderEntity]:
        """List orders belonging to a specific customer."""
        return self.db.query(OrderEntity).filter(OrderEntity.customer_id == customer_id).all()

    def cancel_order(self, order_id: str) -> OrderEntity:
        """Mark an order as CANCELLED and update payment status to REFUNDED."""
        order = self.get_by_id_or_raise(order_id)
        order.status = "CANCELLED"
        order.payment_status = "REFUNDED"
        order.can_cancel = False
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_status(self, order_id: str, status: str) -> OrderEntity:
        """Update the operational status of an order."""
        order = self.get_by_id_or_raise(order_id)
        order.status = status
        if status in ["PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"]:
            order.can_cancel = False
        self.db.commit()
        self.db.refresh(order)
        return order
