# Cloud Provisioning & Observability

Use this when the task involves sizing, provisioning, securing, or monitoring cloud infrastructure (AWS/GCP/Azure/Vercel-style platforms alike — the concepts transfer even though the console/CLI differs).

## Sizing (start small, prove the need to grow)

- Default to the smallest instance/tier that meets the current baseline (see SKILL.md step 2), not the one that "should handle anything." Autoscaling or a documented upgrade path covers growth; paying for headroom nobody's using doesn't.
- Serverless/managed (Lambda, Cloud Run, managed Postgres) over self-managed for anything without a specific reason to self-host (cost at extreme scale, a compliance requirement, a need for OS-level control). Ops burden is a real cost — count it.
- Multi-region and multi-AZ are reliability decisions, not defaults — justify with an actual uptime SLA or compliance requirement. A side project doesn't need three availability zones.

## IAM & networking

- Least-privilege by default: scope roles/policies to the specific resources and actions needed, not `*:*`. Start narrow, widen only when a real error demands it.
- Network boundaries: private subnets for anything that doesn't need direct internet exposure (databases, internal services); a load balancer or API gateway as the one public entry point.
- Rotate and never commit credentials — use the platform's secrets manager (AWS Secrets Manager, GCP Secret Manager, Vercel env vars) and inject at runtime, not build time where avoidable.

## Cost-aware defaults

- Tag resources by project/environment from day one — untagged spend is undiagnosable spend later.
- Set budget alerts before spend happens, not after a surprise bill.
- Turn off or scale down non-production environments outside business hours where nothing depends on 24/7 uptime (staging, dev, preview environments).

## Observability (logging, metrics, alerting)

- Three pillars, don't skip any: **logs** (what happened), **metrics** (how much/how often, over time), **traces** (where time went across a request) — for anything beyond a single-service toy, traces matter as soon as more than one service is in the request path.
- Alert on symptoms users feel (error rate, latency, availability), not just resource internals (CPU, memory) — a healthy-looking CPU graph during an outage is a useless alert.
- Every alert needs an owner and a runbook link — an alert nobody acts on is noise, and noisy alerting trains people to ignore real ones.
- Structured logging (JSON, consistent fields) over free-text from the start — retrofitting log parsing after an incident is the wrong time to learn this.

## Verify before asserting

Cloud provider "best practices" change (service tiers, pricing, default limits, new managed offerings). If a recommendation leans on a specific current price, quota, or "this is the new recommended approach" claim, verify it against the provider's own current docs before presenting it as fact — don't state a specific number or a "now recommended" pattern from memory alone.
