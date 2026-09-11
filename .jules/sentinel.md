## 2024-05-24 - [Defense in Depth: Security Headers]
**Vulnerability:** Missing fundamental security headers on HTTP responses.
**Learning:** Even internal sidecar APIs should implement basic security headers (like Content-Security-Policy, Strict-Transport-Security, X-Frame-Options) as a defense-in-depth measure against client-side attacks, especially if the API ever gets exposed or consumed by a frontend application.
**Prevention:** Implement a global middleware in the FastAPI application to automatically attach security headers to all responses.

## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks (`StartLine`/`EndLine`) for edits to `schema.prisma`, `index.ts`, `public/index.php`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.


## 2024-05-24 - [DoS Protection: Payload Size Limits]
**Vulnerability:** API endpoints accepted unbounded lists in JSON payloads (e.g., `OptimizeRequest`, `AnomalyDetectRequest`), leading to potential algorithmic complexity Denial of Service (DoS) attacks due to O(N^2) or higher complexity operations on those lists.
**Learning:** Pydantic's default `List` typing does not enforce length limits. In applications processing large data structures, especially for complex operations like anomaly detection or routing optimization, unbounded lists can lead to CPU or memory exhaustion.
**Prevention:** Always enforce a reasonable `max_length` (e.g., `max_length=10000`) for all array/list inputs using Pydantic's `Field` validation to protect against payload-based DoS attacks.

## 2024-05-24 - [DoS Protection: String and Regex Validation]
**Vulnerability:** API endpoints lacked strict validation on string inputs like IDs and periods.
**Learning:** Relying solely on type hints without enforcing length limits or regex patterns leaves the application vulnerable to malicious payload-based attacks and data formatting issues.
**Prevention:** Apply `max_length` and `pattern` (regex) constraints consistently using Pydantic's `Field` for request models and FastAPI's `Query` for route parameters to ensure data integrity and prevent potential exploits.
## 2025-02-14 - Fix Missing Input Validation on Rebalance Optimizer
**Vulnerability:** Found multiple Pydantic models in `app/rebalance_optimizer.py` that had missing length limits on strings (e.g., `id`, `name`, `sku`, `warehouse_id`) and missing non-negative bounds on numeric fields (e.g., `on_hand`, `in_transit`, `transit_days`, `cost_per_unit`).
**Learning:** Pydantic by default accepts arbitrarily long strings and allows negative values for ints/floats unless explicitly constrained with `max_length` and bounds like `ge=0`. Missing these limits exposes the application to string allocation DoS (denial of service) and potential crashes or logic bugs.
**Prevention:** Always use the `Field(..., max_length=255)` for string fields and `ge=0` (or appropriate bounds) for numerical values that represent physical quantities, weights, times, or costs in request models to enforce secure data boundaries.
