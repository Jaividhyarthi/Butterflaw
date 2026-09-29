"""Deployment history for the demo team (an Indian e-commerce platform).

Synthetic but realistic. The team has specific failure patterns that generic
intuition misses (for example: pg-driver 3.2 bumps break PgBouncer; Friday
17:00-19:00 checkout deploys collide with the weekly price-sync job). Those
patterns only become visible through memory of past outcomes.

HISTORY is retained into Hindsight when a memory bank is created.
REPLAY is replayed in order: the agent predicts BEFORE seeing each outcome,
then the real outcome is retained so the agent can learn from it.
"""

SERVICES = [
    "payment-api", "checkout-service", "db-config", "auth-service",
    "redis-cache", "inventory-service", "notification-service", "k8s-platform",
]

# ---- Team history known before the replay starts (July 2026) ----
HISTORY = [
    {
        "id": "INC-127", "version": "v3.4.0", "when": "2026-07-14T14:20:00",
        "services": ["db-config", "payment-api"],
        "summary": "Raised DB connection pool max from 40 to 100 and shipped payment-api retry changes in the same release",
        "failed": True,
        "root_cause": "New pool size exhausted Postgres max_connections while payment-api retries multiplied load; "
                      "p99 latency hit 9s, 18% of checkouts failed for 47 minutes (approx Rs 32 lakh GMV lost).",
    },
    {
        "id": "INC-131", "version": "v2.6.2", "when": "2026-07-21T12:05:00",
        "services": ["redis-cache", "auth-service"],
        "summary": "Changed redis session eviction policy to allkeys-lru and rolled auth-service token refresh logic",
        "failed": True,
        "root_cause": "Eviction dropped live session keys; 41,000 users were logged out mid-checkout and "
                      "auth-service hit a 401 storm for 25 minutes.",
    },
    {
        "id": "INC-134", "version": "v1.7.0", "when": "2026-07-24T11:40:00",
        "services": ["notification-service"],
        "summary": "Updated order-confirmation email templates",
        "failed": True,
        "root_cause": "A missing template variable crashed the email worker and 12,000 emails queued for 3 hours. "
                      "STRUCTURAL FIX: templates are now schema-validated in CI, so template changes no longer reach "
                      "production broken.",
    },
    {
        "id": "DEP-0712", "version": "v2.8.0", "when": "2026-07-28T10:30:00",
        "services": ["inventory-service"],
        "summary": "Large 1,400-line refactor of stock reservation logic, shipped dark behind feature flag inv-reserve-v2",
        "failed": False,
        "root_cause": "",
    },
    {
        "id": "DEP-0719", "version": "v3.4.3", "when": "2026-07-30T15:10:00",
        "services": ["payment-api"],
        "summary": "New refund status webhook in payment-api, rolled out through a 5% canary for 2 hours",
        "failed": False,
        "root_cause": "",
    },
]

# ---- Deployments replayed in order (Aug-Sep 2026) ----
REPLAY = [
    {"id": "DEP-0803", "version": "v4.1.0", "when": "2026-08-03T11:05:00", "services": ["checkout-service"],
     "summary": "Refactor checkout pricing module (1,200 lines) behind feature flag checkout-pricing-v2, dark launch",
     "failed": False, "root_cause": ""},
    {"id": "INC-139", "version": "v2.9.3", "when": "2026-08-05T15:40:00", "services": ["inventory-service"],
     "summary": "Minor dependency bump: pg-driver 3.1.4 -> 3.2.0",
     "failed": True, "root_cause": "pg-driver 3.2 caches prepared statements by default; PgBouncer in transaction "
     "pooling mode rejected them and 40% of inventory reads failed for 31 minutes."},
    {"id": "INC-140", "version": "v4.1.1", "when": "2026-08-07T17:30:00", "services": ["checkout-service"],
     "summary": "Fix typo in checkout success banner copy",
     "failed": True, "root_cause": "Friday 17:30 deploy restarted checkout pods during the weekly 17:45 catalog "
     "price-sync job; the cache warmed with stale prices and 22 minutes of orders were mispriced."},
    {"id": "DEP-0810", "version": "v1.8.0", "when": "2026-08-10T10:15:00", "services": ["notification-service"],
     "summary": "Rewrite order-confirmation email templates for new branding",
     "failed": False, "root_cause": ""},
    {"id": "INC-142", "version": "v3.7.0", "when": "2026-08-12T14:00:00", "services": ["db-config", "payment-api"],
     "summary": "Raise DB connection pool max from 50 to 120 and ship payment-api retry changes in the same release",
     "failed": True, "root_cause": "Same failure mode as INC-127: Postgres max_connections exhausted, payment "
     "timeouts for 19 minutes."},
    {"id": "INC-143", "version": "v2.9.4", "when": "2026-08-13T12:30:00", "services": ["auth-service"],
     "summary": "Routine library update: pg-driver 3.1.4 -> 3.2.0 in auth-service",
     "failed": True, "root_cause": "Prepared-statement caching in pg-driver 3.2 broke behind PgBouncer; logins failed "
     "for 14 minutes."},
    {"id": "INC-145", "version": "v2.10.0", "when": "2026-08-17T16:00:00", "services": ["k8s-platform", "inventory-service"],
     "summary": "Lower inventory-service memory limit from 1Gi to 512Mi to cut cluster cost",
     "failed": True, "root_cause": "Pods were OOMKilled during the nightly stock reconciliation; stock counts went "
     "stale and 600 orders were oversold."},
    {"id": "DEP-0819", "version": "v3.8.0", "when": "2026-08-19T11:20:00", "services": ["payment-api"],
     "summary": "Add UPI Autopay mandate endpoint, 5% canary for 2 hours",
     "failed": False, "root_cause": ""},
    {"id": "INC-147", "version": "v4.2.1", "when": "2026-08-21T17:50:00", "services": ["checkout-service"],
     "summary": "Update GST rounding helper (2-line change)",
     "failed": True, "root_cause": "Friday evening deploy again collided with the weekly price-sync job; stale "
     "prices served for 18 minutes."},
    {"id": "INC-149", "version": "v2.7.0", "when": "2026-08-24T13:10:00", "services": ["redis-cache", "auth-service"],
     "summary": "Change session key TTL from 24h to 12h and roll auth-service token refresh in the same deploy",
     "failed": True, "root_cause": "Session keys expired mid-flight while token refresh logic changed; mass logouts "
     "for 20 minutes."},
    {"id": "DEP-0826", "version": "v2.11.0", "when": "2026-08-26T10:40:00", "services": ["inventory-service"],
     "summary": "Schema migration adding reserved_qty column using expand/contract, backfill in batches of 5,000",
     "failed": False, "root_cause": ""},
    {"id": "DEP-0827", "version": "v1.9.0", "when": "2026-08-27T15:15:00", "services": ["notification-service"],
     "summary": "Add WhatsApp message template for shipping updates",
     "failed": False, "root_cause": ""},
    {"id": "INC-152", "version": "v3.8.2", "when": "2026-08-31T11:00:00", "services": ["payment-api"],
     "summary": "Bump pg-driver to 3.2.1 in payment-api",
     "failed": True, "root_cause": "pg-driver 3.2.x prepared-statement caching broke behind PgBouncer; UPI payment "
     "confirmations failed for 9 minutes."},
    {"id": "DEP-0902", "version": "v4.3.0", "when": "2026-09-02T16:30:00", "services": ["checkout-service"],
     "summary": "Cart API pagination for large carts",
     "failed": False, "root_cause": ""},
    {"id": "INC-154", "version": "v4.3.2", "when": "2026-09-04T17:20:00", "services": ["checkout-service", "notification-service"],
     "summary": "Tweak checkout confirmation event payload",
     "failed": True, "root_cause": "Third Friday-evening checkout deploy to overlap the price-sync job; stale "
     "prices plus duplicate confirmation emails."},
    {"id": "INC-156", "version": "v2.12.0", "when": "2026-09-07T12:00:00", "services": ["k8s-platform", "inventory-service"],
     "summary": "Reduce inventory-service CPU request and set memory limit to 600Mi",
     "failed": True, "root_cause": "OOMKilled again during stock reconciliation; the job needs about 850Mi at peak."},
    {"id": "DEP-0909", "version": "v3.9.0", "when": "2026-09-09T14:45:00", "services": ["db-config"],
     "summary": "Tune DB statement timeout from 30s to 20s, no service code changes",
     "failed": False, "root_cause": ""},
    {"id": "DEP-0910", "version": "v2.8.0", "when": "2026-09-10T11:30:00", "services": ["auth-service"],
     "summary": "Large OAuth provider refactor behind feature flag auth-oidc-v2, dark launch",
     "failed": False, "root_cause": ""},
    {"id": "INC-158", "version": "v4.3.5", "when": "2026-09-11T17:40:00", "services": ["checkout-service"],
     "summary": "Hotfix: null check in coupon validation",
     "failed": True, "root_cause": "Friday 17:40 deploy during price-sync; stale prices for 15 minutes."},
    {"id": "INC-160", "version": "v3.10.0", "when": "2026-09-14T15:00:00", "services": ["db-config", "payment-api"],
     "summary": "Change DB pool idle timeout and deploy payment-api refund flow together",
     "failed": True, "root_cause": "Pool churn plus refund retries exhausted connections; refunds stuck for 26 minutes."},
    {"id": "DEP-0916", "version": "v2.8.0", "when": "2026-09-16T10:05:00", "services": ["redis-cache"],
     "summary": "Increase redis maxmemory from 4GB to 6GB",
     "failed": False, "root_cause": ""},
    {"id": "DEP-0918", "version": "v4.4.0", "when": "2026-09-18T11:00:00", "services": ["checkout-service"],
     "summary": "Checkout address autocomplete (Friday morning release)",
     "failed": False, "root_cause": ""},
    {"id": "INC-163", "version": "v1.10.1", "when": "2026-09-22T13:30:00", "services": ["notification-service"],
     "summary": "Bump pg-driver to 3.2.1 in notification-service",
     "failed": True, "root_cause": "Same pg-driver 3.2 / PgBouncer prepared-statement failure; notifications "
     "stalled for 11 minutes."},
    {"id": "INC-165", "version": "v2.13.0", "when": "2026-09-24T16:10:00", "services": ["inventory-service"],
     "summary": "Switch inventory-service JSON serializer to orjson for speed",
     "failed": True, "root_cause": "Novel failure: orjson serialised Decimal stock values differently and "
     "fractional-unit SKUs were rounded."},
]
