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


# ---- Incident details for the UI (impact, trail, resolution). Display only; not part of the retained text. ----
INCIDENT_DETAILS = {
    "INC-127": {"title": "Checkout outage after pool resize + payment retries", "severity": "high",
                "failed_requests": 48200, "amount_inr": 3200000, "downtime_min": 47, "fix_type": "patch",
                "trail": ["DB pool max raised 40 -> 100", "payment-api retries multiplied load", "Postgres max_connections exhausted", "18% of checkouts failed"],
                "resolution": "Rolled back pool size; capped retries with jittered backoff."},
    "INC-131": {"title": "Mass logouts after redis eviction change", "severity": "high",
                "failed_requests": 41000, "amount_inr": 950000, "downtime_min": 25, "fix_type": "patch",
                "trail": ["Eviction policy set to allkeys-lru", "Live session keys evicted", "auth-service 401 storm", "41,000 users logged out mid-checkout"],
                "resolution": "Restored volatile-lru; moved sessions to a dedicated redis db."},
    "INC-134": {"title": "Email worker crash on template variable", "severity": "medium",
                "failed_requests": 12000, "amount_inr": 0, "downtime_min": 180, "fix_type": "structural",
                "trail": ["Template updated without a variable", "Email worker crashed", "Queue backed up", "12,000 emails delayed 3 hours"],
                "resolution": "Structural fix: templates are schema-validated in CI."},
    "INC-139": {"title": "Inventory reads failing after pg-driver 3.2", "severity": "high",
                "failed_requests": 26500, "amount_inr": 410000, "downtime_min": 31, "fix_type": "patch",
                "trail": ["pg-driver 3.1.4 -> 3.2.0", "Prepared statements cached by default", "PgBouncer (transaction mode) rejected them", "40% of inventory reads failed"],
                "resolution": "Pinned pg-driver 3.1.4; set prepare_threshold=0."},
    "INC-140": {"title": "Mispriced orders during Friday price-sync", "severity": "high",
                "failed_requests": 3100, "amount_inr": 780000, "downtime_min": 22, "fix_type": "patch",
                "trail": ["Friday 17:30 checkout deploy", "Pods restarted during 17:45 price-sync", "Cache warmed with stale prices", "22 minutes of mispriced orders"],
                "resolution": "Rolled back and re-warmed the price cache."},
    "INC-142": {"title": "Payment timeouts after pool resize (repeat of INC-127)", "severity": "high",
                "failed_requests": 21400, "amount_inr": 1450000, "downtime_min": 19, "fix_type": "patch",
                "trail": ["DB pool max raised 50 -> 120", "payment-api retry changes in same release", "Postgres max_connections exhausted", "Payment timeouts for 19 minutes"],
                "resolution": "Rolled back; pool changes now ship separately from payment-api."},
    "INC-143": {"title": "Login failures after pg-driver 3.2 in auth-service", "severity": "high",
                "failed_requests": 18900, "amount_inr": 260000, "downtime_min": 14, "fix_type": "patch",
                "trail": ["pg-driver 3.1.4 -> 3.2.0", "Prepared-statement caching", "PgBouncer rejected statements", "Logins failed for 14 minutes"],
                "resolution": "Pinned pg-driver; disabled prepared-statement cache."},
    "INC-145": {"title": "Oversold stock after memory limit cut", "severity": "high",
                "failed_requests": 900, "amount_inr": 540000, "downtime_min": 38, "fix_type": "patch",
                "trail": ["Memory limit 1Gi -> 512Mi", "Nightly reconciliation hit the limit", "Pods OOMKilled", "600 orders oversold"],
                "resolution": "Restored 1Gi limit; added memory alert on the reconciliation job."},
    "INC-147": {"title": "Stale prices on second Friday-evening deploy", "severity": "medium",
                "failed_requests": 2600, "amount_inr": 610000, "downtime_min": 18, "fix_type": "patch",
                "trail": ["Friday 17:50 checkout deploy", "Collided with weekly price-sync", "Stale prices cached", "18 minutes of wrong prices"],
                "resolution": "Rolled back; cache re-warmed."},
    "INC-149": {"title": "Mass logouts after session TTL + token refresh change", "severity": "high",
                "failed_requests": 33000, "amount_inr": 720000, "downtime_min": 20, "fix_type": "patch",
                "trail": ["Session TTL 24h -> 12h", "Token refresh changed in same deploy", "Sessions expired mid-flight", "Mass logouts for 20 minutes"],
                "resolution": "Reverted TTL; token refresh shipped separately with a canary."},
    "INC-152": {"title": "UPI confirmations failing after pg-driver 3.2.1", "severity": "high",
                "failed_requests": 9800, "amount_inr": 1100000, "downtime_min": 9, "fix_type": "patch",
                "trail": ["pg-driver bumped to 3.2.1", "Prepared-statement caching", "PgBouncer rejected statements", "UPI confirmations failed for 9 minutes"],
                "resolution": "Pinned pg-driver 3.1.4 across payment-api."},
    "INC-154": {"title": "Stale prices + duplicate emails on Friday deploy", "severity": "medium",
                "failed_requests": 4200, "amount_inr": 530000, "downtime_min": 21, "fix_type": "patch",
                "trail": ["Friday 17:20 checkout payload change", "Overlapped weekly price-sync", "Stale prices + event replays", "Duplicate confirmation emails"],
                "resolution": "Rolled back; deduplicated the event consumer."},
    "INC-156": {"title": "OOMKilled again at 600Mi", "severity": "high",
                "failed_requests": 700, "amount_inr": 380000, "downtime_min": 27, "fix_type": "patch",
                "trail": ["Memory limit set to 600Mi", "Reconciliation peaks at ~850Mi", "Pods OOMKilled", "Stock counts stale"],
                "resolution": "Limit restored to 1Gi; reconciliation moved to a separate job."},
    "INC-158": {"title": "Stale prices after Friday coupon hotfix", "severity": "medium",
                "failed_requests": 2100, "amount_inr": 420000, "downtime_min": 15, "fix_type": "patch",
                "trail": ["Friday 17:40 coupon hotfix", "Deployed during price-sync", "Stale price cache", "15 minutes of wrong prices"],
                "resolution": "Rolled back; deploy freeze proposed for Fri 17:00-19:00."},
    "INC-160": {"title": "Refunds stuck after pool timeout + refund flow", "severity": "high",
                "failed_requests": 7600, "amount_inr": 890000, "downtime_min": 26, "fix_type": "patch",
                "trail": ["DB pool idle timeout changed", "Refund flow shipped in same release", "Pool churn + refund retries", "Refunds stuck for 26 minutes"],
                "resolution": "Rolled back pool config; refund flow re-shipped alone."},
    "INC-163": {"title": "Notifications stalled after pg-driver 3.2.1", "severity": "medium",
                "failed_requests": 5400, "amount_inr": 0, "downtime_min": 11, "fix_type": "patch",
                "trail": ["pg-driver bumped to 3.2.1", "Prepared-statement caching", "PgBouncer rejected statements", "Notifications stalled 11 minutes"],
                "resolution": "Pinned pg-driver; added a CI check blocking pg-driver 3.2.x."},
    "INC-165": {"title": "Rounded stock values after orjson switch", "severity": "medium",
                "failed_requests": 1300, "amount_inr": 150000, "downtime_min": 44, "fix_type": "patch",
                "trail": ["JSON serializer switched to orjson", "Decimal serialised differently", "Fractional stock values rounded", "Wrong stock on fractional-unit SKUs"],
                "resolution": "Reverted serializer; added Decimal round-trip tests."},
}

DEPENDENCIES = [
    ("checkout-service", "payment-api", "calls"), ("checkout-service", "inventory-service", "calls"),
    ("checkout-service", "redis-cache", "reads"), ("checkout-service", "notification-service", "emits events"),
    ("payment-api", "db-config", "depends on"), ("inventory-service", "db-config", "depends on"),
    ("auth-service", "redis-cache", "sessions"), ("auth-service", "db-config", "depends on"),
    ("notification-service", "db-config", "depends on"), ("inventory-service", "k8s-platform", "runs on"),
    ("checkout-service", "k8s-platform", "runs on"), ("payment-api", "k8s-platform", "runs on"),
    ("auth-service", "k8s-platform", "runs on"), ("notification-service", "k8s-platform", "runs on"),
]

DEFAULT_GUARDRAILS = [
    {"id": "GR-1", "rule": "Block releases that change db-config and payment-api together without a canary.", "source": "INC-127", "added": "2026-07-15"},
    {"id": "GR-2", "rule": "Require a cache/session flush plan when auth-service token logic and redis session settings change together.", "source": "INC-131", "added": "2026-07-22"},
    {"id": "GR-3", "rule": "Reject inventory-service memory limit reductions without a load test of the nightly reconciliation job.", "source": "INC-145", "added": "2026-08-18"},
]
