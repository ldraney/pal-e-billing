# Pal-E Billing

Billing portal for the [Pal-E](https://ldraney.github.io/pal-e) AI assistant. Handles Stripe subscription management, webhook processing, and user provisioning for the Pal-E platform.

## Tiers

| Tier | Price | Included Services |
|------|-------|-------------------|
| **Base** | $20/mo | Notion + LinkedIn |
| **Pro** | $50/mo | + Gmail + GCal |
| **Custom** | By appointment | Tailored configuration |

## Architecture

- **FastAPI** service running on K8s in the `openclaw` namespace
- **Stripe** integration for checkout sessions, subscription lifecycle, and customer portal
- **SQLite** (WAL mode) for subscriber state, keyed by Telegram user ID
- **API key** auth for internal service-to-service calls (OpenClaw gateway queries subscription status)

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/webhook/stripe` | Stripe signature | Receives Stripe webhook events |
| GET | `/status/{telegram_user_id}` | API key | Returns subscription status |
| GET | `/portal/{telegram_user_id}` | API key | Redirects to Stripe customer portal |
| GET | `/health` | None | Health check |

### Webhook Events Handled

- `checkout.session.completed` -- creates/activates subscriber record
- `customer.subscription.updated` -- syncs status changes (active, past_due, unpaid, etc.)
- `customer.subscription.deleted` -- marks subscription as canceled

## Development

```bash
# Install dependencies
pip install -e .

# Required environment variables (or .env file)
export STRIPE_API_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export INTERNAL_API_KEY=your-internal-key

# Run the server
pal-e-billing
# or
uvicorn pal_e_billing.main:app --reload
```

## Related Repos

- [pal-e](https://github.com/ldraney/pal-e) -- Landing page and public docs
- [mcp-gateway-k8s](https://github.com/ldraney/mcp-gateway-k8s) -- K8s infrastructure and OpenClaw config
- [openclaw](https://github.com/ldraney/openclaw) -- Gateway fork with Pal-E customizations

## Status

Active development. Core webhook handler and status API are implemented. Tier-specific product/price configuration in Stripe and checkout flow integration are next.
