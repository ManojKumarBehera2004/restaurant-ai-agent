"""
Database Seeding Script.
Populates SQLite with sample orders, tickets, and operational state.
"""

import json
import os
from datetime import datetime
from app.models.database import SessionLocal, init_db
from app.models.entities import OrderEntity, TicketEntity, AuditLogEntity
from app.core.logging import logger


def seed_database():
    """Seed initial operational data from orders.json."""
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_orders_count = db.query(OrderEntity).count()
        if existing_orders_count > 0:
            logger.info(f"Database already contains {existing_orders_count} orders. Skipping seed.")
            return

        orders_file = os.path.join(os.path.dirname(__file__), "orders.json")
        with open(orders_file, "r", encoding="utf-8") as f:
            orders_data = json.load(f)

        for item in orders_data:
            order = OrderEntity(
                id=item["id"],
                customer_id=item["customer_id"],
                customer_name=item["customer_name"],
                customer_phone=item.get("customer_phone"),
                status=item["status"],
                items_json=json.dumps(item["items"]),
                subtotal=item["subtotal"],
                tax=item["tax"],
                delivery_fee=item["delivery_fee"],
                total=item["total"],
                delivery_address=item["delivery_address"],
                delivery_partner=item.get("delivery_partner"),
                estimated_delivery_minutes=item.get("estimated_delivery_minutes"),
                payment_status=item["payment_status"],
                can_cancel=item["can_cancel"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(order)

        # Seed initial sample support ticket
        initial_ticket = TicketEntity(
            id="TCK-20260928-1001",
            idempotency_key="seed-ticket-1",
            customer_id="CUST-004",
            order_id="ORD-1006",
            category="Payment",
            priority="High",
            sentiment="Urgent",
            issue_summary="Payment captured but order marked failed",
            details="Customer bank debited $29.11, but order failed during checkout sync. Needs refund verification.",
            resolution_action="Escalated to billing reconciliation queue",
            status="OPEN",
            created_at=datetime.utcnow()
        )
        db.add(initial_ticket)

        # Seed audit log
        audit_log = AuditLogEntity(
            event_type="SYSTEM_SEED",
            session_id="system",
            message="Initial operational database seeded with sample orders and policies.",
            payload_json=json.dumps({"orders_count": len(orders_data), "tickets_count": 1}),
            timestamp=datetime.utcnow()
        )
        db.add(audit_log)

        db.commit()
        logger.info(f"Successfully seeded {len(orders_data)} orders and sample tickets into database.")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
