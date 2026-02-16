# Pal-E Billing -- Agent Instructions

## Project Overview

This is the Pal-E billing portal -- a FastAPI service that handles Stripe subscription management for the Pal-E AI assistant platform.

## Tech Stack

- Python 3.12+
- FastAPI + Uvicorn
- Stripe SDK (v11+)
- SQLite with WAL mode
- Pydantic Settings for config

## Integration Points

- **Stripe**: Checkout sessions, webhooks, customer portal. Products/prices must be configured in Stripe Dashboard (test mode first, then production).
- **OpenClaw gateway** (`mcp-gateway-k8s`): Queries `/status/{telegram_user_id}` to check if a user has an active subscription before allowing access to paid MCP tools.
- **Telegram**: User IDs are the primary key. `client_reference_id` in Stripe checkout sessions maps to Telegram user ID.
- **K8s**: Deployed in the `openclaw` namespace alongside other Pal-E services. SQLite DB persisted via PVC at `/data/billing/billing.db`.

## Tier Definitions

Defined in ldraney/pal-e#14:

| Tier | Price | Services |
|------|-------|----------|
| Base | $20/mo | Notion, LinkedIn |
| Pro | $50/mo | Notion, LinkedIn, Gmail, GCal |
| Custom | By appointment | Tailored |

## Architecture Decisions

Tracked in:
- Notion project page: https://www.notion.so/Pal-E-308c2a379fe0815db2d4fdf80e6e39cb
- mcp-gateway-k8s#59 (if it exists)

## Key Files

- `src/pal_e_billing/main.py` -- FastAPI app, health and status endpoints
- `src/pal_e_billing/stripe_webhook.py` -- Stripe webhook handler
- `src/pal_e_billing/portal.py` -- Customer portal redirect
- `src/pal_e_billing/db.py` -- SQLite subscriber store
- `src/pal_e_billing/auth.py` -- API key authentication
- `src/pal_e_billing/config.py` -- Pydantic settings

## Environment Variables

| Variable | Description |
|----------|-------------|
| `STRIPE_API_KEY` | Stripe secret key (sk_test_... or sk_live_...) |
| `STRIPE_WEBHOOK_SECRET` | Webhook endpoint signing secret (whsec_...) |
| `INTERNAL_API_KEY` | Shared key for service-to-service auth |
| `DB_PATH` | SQLite database path (default: `/data/billing/billing.db`) |
| `HOST` | Bind address (default: `0.0.0.0`) |
| `PORT` | Bind port (default: `8004`) |
| `PORTAL_RETURN_URL` | URL to return to after Stripe portal (default: Telegram bot link) |

## CRITICAL: Fork Safety

This is `ldraney/pal-e-billing`. There is no upstream. All work targets this repo only.

## Development Rules

- Never commit `.env` files or secrets
- Always test Stripe webhook handling with `stripe listen --forward-to localhost:8004/webhook/stripe`
- Run `pip install -e .` for development installs
- SQLite DB files (`*.db`) are gitignored
