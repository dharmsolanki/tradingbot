# PROJECT_AUDIT.md

# Trading Bot Production Audit & Improvement Roadmap

Version: 2.0
Status: ACTIVE
Project State: Under Production Hardening

================================================================================
IMPORTANT INSTRUCTIONS FOR CLAUDE
================================================================================

Read this document completely before making any changes.

This document is the single source of truth for the project.

Never ignore it.

================================================================================
WORKFLOW (MANDATORY)
================================================================================

For EVERY conversation:

1. Read PROJECT_AUDIT.md
2. Find the FIRST incomplete task.
3. Work ONLY on that task.
4. Verify it completely.
5. Update this document.
6. Stop.

DO NOT continue to the next task.

================================================================================
STRICT RULES
================================================================================

DO NOT

❌ Perform multiple tasks in one conversation.

❌ Refactor unrelated code.

❌ Rewrite complete files unless absolutely necessary.

❌ Change architecture without reason.

❌ Repeat already completed work.

❌ Modify completed tasks unless a regression exists.

❌ Change formatting only.

❌ Rename files without necessity.

❌ Introduce breaking API changes.

❌ Remove backward compatibility.

================================================================================
ALWAYS
================================================================================

✔ Keep changes minimal.

✔ Keep architecture intact.

✔ Preserve public APIs.

✔ Verify every modification.

✔ Fix regressions immediately.

✔ Keep commits small.

✔ Stop after ONE completed task.

================================================================================
PROJECT GOAL
================================================================================

Create a production-ready options trading bot.

The bot should be

- Reliable
- Stable
- Fast
- Safe
- Capital-aware
- Recoverable
- Maintainable

================================================================================
CURRENT PROJECT STATUS
================================================================================

Backend

✔ FastAPI

✔ SQLite

✔ Upstox API

✔ Recommendation Engine

✔ Paper Trading

✔ HTML Frontend

Current State

NOT Production Ready

================================================================================
COMPLETED TASKS
================================================================================

P0-001

Title

HTTP Retry + Exponential Backoff

Status

Completed

Files

app/market_data.py

Completed

✔ Retry

✔ Timeout Retry

✔ Connection Retry

✔ HTTP 429 Retry

✔ HTTP 5xx Retry

Validation

✔ Syntax

✔ Manual Review

Regression

None

================================================================================
PENDING TASKS
================================================================================

===============================================================================
PRIORITY 0
Production Blocking
===============================================================================

P0-002

Title

Remove Blocking Network Calls From Async Loops

Priority

Critical

Estimated Token Cost

Medium

Files

main.py

Definition of Done

- No synchronous HTTP calls inside async loops.
- Event loop never blocks.
- Slow API cannot freeze bot.

Regression Checklist

- Startup
- Live Loop
- Background Tasks

-------------------------------------------------------------------------------

P0-003

Title

Remove Duplicate API Requests

Priority

Critical

Files

recommendation_engine.py

main.py

Definition of Done

Exactly one market fetch per decision cycle.

-------------------------------------------------------------------------------

P0-004

Title

Market Status Service

Priority

Critical

Create

market_status.py

Must Detect

OPEN

CLOSED

HOLIDAY

DATA_DELAYED

NO_DATA

No hardcoded assumptions.

-------------------------------------------------------------------------------

P0-005

Title

Market Data Freshness Validation

Dependency

Requires P0-004

Files

market_data.py

Definition of Done

Reject delayed candles ONLY during market hours.

-------------------------------------------------------------------------------

P0-006

Title

Startup Recovery

Restore

Open trade

Recommendation

Trailing Stop

Runtime State

-------------------------------------------------------------------------------

P0-007

Title

Crash Recovery

Bot restart must never duplicate trades.

-------------------------------------------------------------------------------

P0-008

Title

Duplicate Trade Prevention

Prevent

Duplicate recommendation

Duplicate order

Duplicate paper trade

-------------------------------------------------------------------------------

P0-009

Title

Thread Safety Review

Repositories

SQLite

Shared State

-------------------------------------------------------------------------------

P0-010

Title

Async Safety Review

Review

await

sleep

blocking calls

event loop

===============================================================================
PRIORITY 1
Trading Logic
===============================================================================

P1-001

Capital Management

Review

Position sizing

Lot sizing

Margin

Affordability

Capital allocation

-------------------------------------------------------------------------------

P1-002

Risk Engine

Review

SL

Target

Risk %

Drawdown

Daily Loss

-------------------------------------------------------------------------------

P1-003

Recommendation Engine

Review

Duplicate evaluate()

Confidence

Filters

-------------------------------------------------------------------------------

P1-004

Option Selection

Improve

Liquidity

Open Interest

IV

Spread

Delta

Affordability

Expiry Selection

-------------------------------------------------------------------------------

P1-005

Trailing Stop

Review

RR Trigger

Profit Lock

Partial Exit

===============================================================================
PRIORITY 2
Performance
===============================================================================

P2-001

Caching

Reduce API calls.

-------------------------------------------------------------------------------

P2-002

Database Optimization

Indexes

Queries

Transactions

-------------------------------------------------------------------------------

P2-003

Memory Review

Leaks

Object Lifetime

-------------------------------------------------------------------------------

P2-004

Logging

Structured logging

Log levels

Rotation

===============================================================================
PRIORITY 3
Security
===============================================================================

P3-001

Configuration Validation

Validate

API Key

Access Token

Capital

Risk %

Database

Startup should fail fast.

-------------------------------------------------------------------------------

P3-002

Secrets Handling

Review

Tokens

Sensitive Config

===============================================================================
PRIORITY 4
Frontend
===============================================================================

P4-001

Dashboard

Improve

Refresh

Reconnect

WebSocket Stability

-------------------------------------------------------------------------------

P4-002

Error Handling

Better user messages.

===============================================================================
KNOWN ISSUES
===============================================================================

Keep this section updated.

If a bug is intentionally postponed, move it here.

Never silently ignore issues.

===============================================================================
REGRESSION CHECKLIST
===============================================================================

Every completed task MUST verify

✔ Syntax

✔ Imports

✔ Startup

✔ Unit Tests

✔ Existing Features

✔ No Duplicate Calls

✔ No Duplicate Trades

✔ No Deadlocks

✔ No Thread Issues

✔ No Async Blocking

================================================================================
CHANGE LOG
================================================================================

Every completed task MUST append

Date

Task ID

Files Changed

Reason

Summary

Validation

Regression Risk

Next Task

================================================================================
FINAL PRODUCTION CHECKLIST
================================================================================

Before deployment verify

✔ Retry

✔ Timeout Recovery

✔ HTTP 429

✔ HTTP 5xx

✔ Startup Recovery

✔ Crash Recovery

✔ Duplicate Trade Prevention

✔ Market Status

✔ Freshness Validation

✔ Capital Awareness

✔ Risk Management

✔ Logging

✔ Configuration Validation

✔ Thread Safety

✔ Async Safety

✔ Performance

✔ API Stability

✔ Database Stability

✔ Production Readiness

================================================================================
END OF DOCUMENT
================================================================================