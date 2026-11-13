# ModelOps V1: credential pool, task routing and transport registry

Scope: backendV1 only. Policies are server-managed ModelOps DB data. They do
not grant workspace access and do not modify source evidence or an index.

## API and administration

All routes below are under `/platform/v1alpha1` and require `ai.models.manage`:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/modelops/registry` | Executable adapter contracts shared with FE |
| GET / PUT | `/modelops/providers/{id}/resilience` | Read / replace explicit policy |
| GET | `/modelops/providers/{id}/executions` | Latest 50 safe runtime attempts |

The existing key listing adds `lease_until`, `cooldown_until` and
`consecutive_failures`; it never returns a lease owner token or credential.

Policy fields: `key_pool_enabled` (default false), `retry_owner` (`qnu` or
`gateway`), `max_key_attempts` (1–3, including the first call), configurable
auth/rate cooldown seconds (1–86400), and ordered `fallbacks` lists per task.
Gateway ownership or a disabled pool requires one attempt. Unknown fields,
duplicate targets, self references, unsupported tasks and incompatible
capabilities/adapters are rejected. Each chain contains at most three backups.
Chains are flat; a candidate's own chain is never recursively expanded.

Tasks are `chat`, `answer`, `followup`, `compiler`, `compiler_review`,
`ocr_review`, `ocr` and `rerank`. Embedding model fallback is prohibited.
The workspace default supplies the primary. An explicit provider selection,
including a persisted assistant or durable run target, is always pinned.

Policies are bound to endpoint/model/type. Changing that identity marks a
saved policy stale; its behavior is disabled until an administrator reviews
and saves it again. Existing defaults, capacity, dimension and quotas
are not changed by saving a policy.

## Runtime behavior

1. Authorize the actor/workspace using the existing domain checkpoint.
2. If the caller did not pin a provider, inspect the primary's task chain.
   A disabled primary or one without a ready credential can be skipped.
   A candidate must be active, hold the required capability and a supported
   transport. The system default supplies the primary; workspace access is
   authorized before any candidate is disclosed in traces. Missing
   capacity/context/schema budget fails before HTTP;
   routing never uses another model to evade that error.
3. Pin the selected target, plan its actual capacity and reserve its quota.
   OCR selects once before recording the target. Compiler stores the target
   at run creation. Subsequent execution cannot change the recorded model.
4. Immediately before HTTP, recheck workspace access, active state, endpoint/model
   and committed usage reservation. The internal execution scope carries the
   caller's session factory, so recovery against a different DB does not read
   credentials, leases or usage from the application's original DB.
5. With the pool enabled, serialize selection in PostgreSQL, lease one key,
   commit, then release every DB lock before inference. Priority is ascending;
   equal-priority keys use the least recently updated key. With the pool off,
   the previous priority/creation ordering and one attempt remain in effect.
6. Only a definite HTTP401/429 rejection may rotate to an untried key of the
   **same provider/model**. An observed positive usage count blocks retry.
   HTTP400/403/422, ambiguous5xx, connection/read uncertainty, malformed output
   and cancellation never activate key retry. Invalid requests do not punish
   a healthy key. An anonymous OCR call has no alternative key and is not retried.
7. Failed401/429 keys receive a cooldown; success clears the failure count.
   Retry-After can extend cooldown up to the supported one-day bound. No sleep
   or unbounded loop occurs inside the request. All attempts, DB work and
   cleanup share the original request timeout. An exhausted key pool reports
   an error; the next task can select a pre-dispatch model fallback if configured.

There is no provider/model switch after a request has been sent. In particular,
this is not response-based model retry, an outage monitoring service or a
guarantee of model quality. Uncertain cost retains the existing reserved/unknown
accounting semantics. Final successful usage is settled by the existing domain;
definite rejected key attempts are recorded separately in the operational audit.

## Storage and concurrency

No new migration is needed. Existing `ProviderKey` lease/cooldown/failure columns
are reused. A bounded, expiring UUID ownership map lives under the provider's
protected `extra_config.key_leases_v1`. Acquire and finish lock provider, then
key; revoke/rotate use that same order to avoid a foreign-key audit deadlock.
An expired worker cannot clear another worker's replacement lease. Process loss
leaves a bounded lease expiry (request budget plus a small cleanup allowance).

Runtime audit stores IDs, requested model, capability, attempt number, error
code, upstream status, latency and measured/unknown tokens. `call_id` groups key
attempts; `usage_id` links them to the domain ledger. It stores no prompt, image,
response body, Authorization header, plaintext key or encrypted key. OCR raw
response preservation remains owned by the OCR domain.

Manual discovery/probes remain single diagnostic calls, outside the operational
pool and quota ledger, using generated samples. Diagnostic fingerprints now use
credential identity instead of mutable lease/cooldown timestamps. Pre-upgrade
checks can appear stale once and should be rerun; lease activity does not stale
new checks.

## Registry

The registry describes implemented QNU adapter contracts, independently of a
provider's declared model capabilities and measured diagnostics. OpenAI-compatible
and local transports implement Chat Completions, dense embeddings, rerank and
Nemotron-style image OCR. Nemotron implements OCR. Gemini and PaddleOCR entries
are retained as configurations with no executable adapter. Runtime fails closed
for unsupported combinations.

Responses API, tool calls and streaming are not implemented. Strict JSON metadata
means the adapter can request a schema; it does not certify a model's compliance.
Image/multi-item input metadata is about the implemented input contract, not an
upstream context/batch limit. Existing operator-declared capacity and embedding
dimension remain the source of those constraints, with unknown kept unknown.

See [operator guide](../../docs/quy_trinh/40_modelops_khoa_va_du_phong.md) and
[diagnostics](modelops-diagnostics.md).
