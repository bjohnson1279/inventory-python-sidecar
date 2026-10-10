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

## 2025-02-28 - [DoS Protection: Pydantic Field Bounds]
**Vulnerability:** API endpoints handling numerical bounds and string inputs (e.g. `average_picks_per_hour`, `zone` in `labor_scheduler.py`) lacked constraint boundaries.
**Learning:** Pydantic classes without `Field` constraints expose internal algorithms to edge case errors (e.g., negative metrics impacting heuristics algorithms) and DoS strings.
**Prevention:** Apply strict limits using `Field(..., ge=0)` and `Field(..., max_length=255)` for inputs mapped to algorithms to enforce integrity and bounds.
## 2025-02-28 - [DoS Protection: Integer Bound Limits]
**Vulnerability:** API endpoints mapped unconstrained numerical integer fields directly into calculations and external tools (like IsolationForest in anomaly detector, or grid calculations in optimizers), leading to potential float overflow errors (infinity) or algorithmic DoS.
**Learning:** Broad exception handling masked silent failures where enormous inputs caused math operations to crash internally, effectively bypassing processing pipelines entirely.
**Prevention:** Always enforce reasonable min and max boundaries on integer inputs (`ge=-1000000`, `le=1000000`) using Pydantic's `Field` validation to protect math operations and preserve security tool functionality against extreme edge-case payloads.

## 2025-03-01 - [DoS Protection: Strict Validation for Internal/Response Pydantic Models]
**Vulnerability:** Internal and Response Pydantic models (e.g., `AnomalyAlert`, `SimulationResponse`) lacked explicit bounds (like `max_length`, `ge`) on string and numerical fields, whereas Request models had them.
**Learning:** Even if Request models are validated, intermediate algorithms or data transformation layers might generate unexpectedly massive structures (like deeply concatenated strings or overflow numbers) due to internal logical bugs or cascading failures. Unconstrained internal/response models fail to catch this data bloat, risking memory exhaustion or algorithmic complexity DoS during serialization.
**Prevention:** Apply `Field(..., max_length=X)` and `Field(..., ge=Y)` consistently to *all* Pydantic models (Requests, Responses, and internal schemas) to establish firm boundaries for memory allocation and system egress.
## 2024-05-24 - Unbounded Numeric Fields Causing Overflow DoS
**Vulnerability:** Unbounded Pydantic integer fields can be submitted with extremely large values (e.g. 10**310) which cause Python `OverflowError` when multiplied by floats.
**Learning:** Python automatically handles arbitrarily large integers, but converting them to floats during arithmetic operations fails, leading to unhandled exceptions and 500 Server Errors (DoS).
**Prevention:** Always add explicit upper bounds (e.g. `le=1000000`) to numerical fields in Pydantic models.

## 2024-10-25 - Unconstrained Pydantic Numerical Bounds
**Vulnerability:** Unconstrained numerical Pydantic fields (like int or float) without upper bounds.
**Learning:** These fields can cause memory/CPU denial-of-service (DoS) issues when arbitrarily large inputs are passed to pure Python operations, or overflow errors (`inf`) in machine learning libraries.
**Prevention:** Always apply explicit upper bounds (e.g., `le=1000000` or `le=1000000.0`) to unconstrained Pydantic integer and float fields, especially on input request models.

## Assertiveness, Decisive PR Execution & Comparative Recommendations
- **Proactive & Decisive PR Submission**: Do NOT repeatedly pause to ask permission to open a pull request (e.g., avoid "Would you like me to open a PR for this?", "Can I submit the PR?", "Should I go ahead and create the PR?"). When an optimization, fix, or feature satisfies requirements, passes local test runners/linters, and preserves architectural invariants, proceed decisively to create and submit the Pull Request with a clear, structured summary and rationale.
- **Explicit Recommendations on Options**: When presenting multiple implementation strategies or architecture options (e.g., Option A vs. Option B), NEVER leave the choice open-ended or passive. Always make an explicit, reasoned recommendation (prefixed with `(Recommended)`) based on **overall technical effectiveness**:
  1. *Algorithmic & Complexity Gains*: Time and space complexity impact (O(N*M) -> O(N+M), reduction of nested scans).
  2. *Resource Overhead*: Heap allocations, memory pressure, and GC pause reduction.
  3. *Domain & Architecture Invariants*: Strict backward compatibility, contract stability, and prevention of regression risks.
  4. *Security & Reliability*: Input validation, cryptographic safety, and concurrency safety.
- **Lead with Recommended Path**: State clearly why the recommended solution delivers the highest net value and immediately execute or propose it as the primary course of action rather than asking open-ended questions.

## Scope Verification, Minimal Churn & CI Protection Directives
- **Scope Verification Before Variable Binding**: When adding interactive states or accessibility attributes (e.g. `disabled={loading}`, `aria-busy={loading}`, `isSubmitting`), NEVER assume a variable identifier exists. Always inspect component props, local state hooks (`useState`), or declaration scope first. If not defined, declare the state hook or reuse an existing scope variable. Never introduce TS2304 / TS2552 ("Cannot find name") compile errors.
- **Surgical Edits Only (No Whole-File Formatting)**: Never run whole-file code formatters (Prettier, Black, Pint, rustfmt) across unmodified lines. Changes must be strictly range-scoped and limited to the minimal AST block needed. Avoid noisy quote/whitespace churn that masks real logic changes and causes merge conflicts. Verify with `git diff -w` that non-functional churn is zero.
- **Zero Scratch File Commits**: Never stage or commit ad-hoc verification, patch, or debug scripts (`test.cjs`, `fix_*.cjs`, `fix_*.php`, `patch_*.py`, `patch_*.sh`, `scratch_*`). Execute checks via the project's native test commands (`npm test`, `pytest`, `phpunit`, etc.) and delete temporary scripts before creating git commits.
- **Never Weaken CI Workflows**: Do not modify `.github/workflows/**` to bypass failures (e.g. adding `|| true`, setting `continue-on-error: true`, or commenting out assertions). Always resolve the defect in the source code or test fixture.
- **Explicit Parameter & Variable Types**: In TypeScript files, avoid implicit `any` by always providing explicit types on functions, parameters, and arrow callbacks (e.g. `(id: string) => ...`). Verify zero type errors with `tsc --noEmit` before committing.

## 2026-09-29 - Non-Destructive Security Patching & CI Protection
**Learning:** Security patches must never weaken CI workflow files (`.github/workflows/**`) by appending `|| true` or `continue-on-error: true` to suppress test/build failures. Furthermore, when adding defensive type assertions or input validators in TypeScript, omitting explicit types can introduce `TS7006: Parameter implicitly has an 'any' type`.
**Action:** Never modify CI workflow definitions to bypass test failures; resolve the underlying issue in source code or test fixtures. Always provide explicit types on newly introduced parameters and helper functions. Ensure zero scratch scripts (`fix_*.php`, `test_*.js`) are committed.

## Additive Documentation & Scratch Cleanliness Directives
- **Strictly Additive Journal Updates**: When updating `.jules/*.md`, strictly append new dated entries (`## YYYY-MM-DD - Title`). NEVER delete, truncate, or overwrite historical learnings or previous entries.
- **Substantive Code Diff Requirement**: Pull requests must include substantive code changes in `src/`, `app/`, `lib/`, or `tests/`. Never open PRs that modify only `.jules/*.md` journals or root scratch scripts.
- **Zero Scratch File Commits**: Never commit `*.diff`, `*.patch`, `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `patch_*.py` files. Always remove temporary debugging or verification scripts prior to committing.

## Scope Quarantine, Journaling & Security Test Invariants
- **Strictly Append-Only Journaling**: When adding learnings to `.jules/*.md`, append strictly at the end of the file. Do not rewrite, deduplicate, or remove lines beginning with `## YYYY-MM-DD`.
- **Surgical Scope Quarantine**: Modify only the files directly involved in the issue and their corresponding test fixtures. Do not delete, rename, or perform drive-by cleanups of unrelated root-level scripts or legacy files.
- **Coupled Test Fixture Awareness for Security Invariants**: When changing fail-open fallback behavior (such as hardening decryption to fail closed), always update upstream test mocks that rely on plaintext credentials or mock values.

## 2025-03-02 - [DoS Protection: Base64 Validation Bypass]
**Vulnerability:** The base64 decoding check in `app/cv_gateway.py` used `pass` or failed to pass the `validate=True` flag to `base64.b64decode`, allowing malformed base64 strings to bypass validation checks silently.
**Learning:** Python's `base64.b64decode` will silently discard characters not in the base64 alphabet if `validate=True` is not provided. By only relying on `try...except Exception` without `validate=True`, large arbitrary or malformed string payloads can bypass early rejection logic, potentially leading to downstream exploitation or memory pressure.
**Prevention:** Always use `validate=True` when validating untrusted base64 input in Python (e.g., `base64.b64decode(payload, validate=True)`) to ensure strict adherence to the alphabet and explicitly throw exceptions for invalid payloads.
## 2024-05-24 - [Avoid broad exceptions in Base64 validation]
**Vulnerability:** Broad except Exception block was used to handle Base64 decoding, potentially masking severe bugs or DoS vectors.
**Learning:** Broad exception handling in Base64 decoding hides underlying application or logic bugs (e.g., TypeError).
**Prevention:** Catch explicit validation exceptions like ValueError or binascii.Error.

## 2026-10-04 - Specific Exception Handling for Date Parsing
**Vulnerability:** Catching broad `Exception` during string and ISO date parsing masked potential fatal runtime failures (such as `KeyboardInterrupt`, memory errors, or type errors) and created unpredictable control flows.
**Learning:** Date parsing errors via `datetime.fromisoformat` specifically raise `ValueError`. Catching broad `Exception` violates defensive programming and can mask deeper systemic bugs.
**Prevention:** Catch specific exceptions (`except ValueError:`) around input parsing logic rather than generic `except Exception:`.

## 2026-10-07 - Process Streamlining, Sibling Coalescence & Autoloading Invariants
**Learning:**
1. Fragmenting stub methods across multiple micro-PRs on the same class causes unavoidable sibling merge collisions and wasted CI cycles.
2. Placing multiple domain services into a single file breaks Composer PSR-4 autoloader discovery in PHP, triggering fatal `Class not found` errors.
3. Writing service calls against unverified entity methods causes fatal runtime errors.
4. String-escaping markdown journal updates corrupts rendered formatting.

**Action:**
- **Coalesce Micro-PRs**: When implementing or scaffolding related controller endpoints, stub methods, or repository queries on a single class, consolidate all changes into a single coherent pull request. Never create separate fragmented PRs for each individual method of the same class.
- **Strict PSR-4 Isolation in PHP**: In PHP codebases, place every class, interface, and enum in its own file named `<ClassName>.php` matching its namespace path. Never combine multiple domain classes into a single file.
- **Domain Contract Verification**: Always inspect entity and aggregate root definitions to verify exact method and property names before writing service logic or test fixtures.
- **Clean Markdown Formatting**: Always append journal entries using actual newline characters, never literal string escape sequences.
## 2024-10-10 - [Fix TypeError DoS in datetime parsing]
**Vulnerability:** [Uncaught TypeError during offset-naive and offset-aware datetime subtraction, creating DoS vector]
**Learning:** [Broad exception handling skipped TypeError during timezone calculation]
**Prevention:** [Catch TypeError alongside ValueError during datetime.fromisoformat parsing]
