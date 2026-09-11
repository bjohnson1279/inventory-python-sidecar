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

## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks for edits to `schema.prisma`, `index.ts`, `public/index.php`, `db/schema.rb`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Completeness & Verification Directives
- **Explicit Parameter & Contract Validation**: When creating or modifying API endpoints (Express, Fastify, Rails, Laravel), always implement explicit parameter and request body validation schemas (e.g. `z.string().uuid()`) to prevent unhandled 404/500 fallthroughs.
- **Database Indexing for Queries**: When addressing query bottlenecks or adding query lookup filters, always implement native database index migrations rather than loading collections into memory and performing array filtering (`.filter()`, `.select`).
- **Co-Occurring Dependency Auditing**: When bumping any dependency version, verify that other transitive dependencies do not carry high/critical security advisories (e.g. run `bundler-audit`, `npm audit`). Never introduce a version bump that breaks underlying framework APIs.
- **Self-Verification Before Commit**: Always run syntax checks (`bash -n` for shell scripts, `tsc --noEmit` for TypeScript, linter checks) and targeted test runners locally before opening or updating a PR.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.
