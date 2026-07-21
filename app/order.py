"""
order.py

RESERVED FOR FUTURE BROKER INTEGRATION.

Per current project scope, this application is a manual, demo-only
trading assistant. It must NOT place real orders and must NOT connect
to a broker account.

This module intentionally contains no order-placement logic. It exists
as a placeholder so that when broker integration is explicitly
requested in a future phase, real order routing can be added here
without restructuring the rest of the app (signal_engine, risk,
option_service, paper_trader all stay broker-agnostic).

Do not implement order placement here until explicitly instructed.
"""
