from app.db import DatabaseManager
from app.core.schema import CREATE_BROKER_ORDERS_TABLE
import json
from datetime import datetime, UTC
from typing import Any, Dict


class BrokerOrderRepository:

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.db.execute(CREATE_BROKER_ORDERS_TABLE)

    def create_order(
        self,
        recommendation_id: str,
        response: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> None:
        """
        Save a newly placed broker order.
        """

        data = response.get("data", {})

        now = datetime.now(UTC).isoformat()

        self.db.execute(
            """
            INSERT INTO broker_orders (
                broker_order_id,
                recommendation_id,
                instrument_key,
                symbol,
                transaction_type,
                product,
                order_type,
                quantity,
                requested_price,
                average_price,
                status,
                exchange_order_id,
                raw_response,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("order_id"),
                recommendation_id,
                payload.get("instrument_token"),
                payload.get("symbol"),
                payload.get("transaction_type"),
                payload.get("product"),
                payload.get("order_type"),
                payload.get("quantity"),
                payload.get("price"),
                None,
                "PLACED",
                None,
                json.dumps(response),
                now,
                now,
            ),
        )
