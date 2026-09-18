## 2023-10-27 - O(N*M) Surplus Iteration Bottleneck
**Learning:** In the inventory rebalance optimizer, finding the correct surplus location for a given deficit iterating over a global array of surpluses results in an O(N*M) bottleneck, bringing performance to ~50s on moderate inputs.
**Action:** Replace nested loops filtering data by SKU and Warehouse ID with pre-computed hash maps (surplus_lookup and surpluses_by_sku) initialized in the initial array traversal.

## Prevention Directives for Automated Refactoring
- **Never Overwrite Complete Files**: Always use range-scoped replacement chunks (`StartLine`/`EndLine`) for edits to `schema.prisma`, `index.ts`, `public/index.php`, or DDL SQL scripts.
- **Do Not Remove Core Declarations**: Do not delete existing route registrations or database DDL tables.
- **Environment Isolation Compatibility**: When replacing fallback secrets, preserve test environment execution via `!getenv('APP_ENV')` or `getenv('APP_ENV') === 'testing'`.
- **No Scratch Files**: Never stage or commit `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `test.js` files to git.
- **No Unresolved Conflict Markers**: Never stage or commit files containing Git merge conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`, `|||||||`). Always resolve conflicts cleanly before committing.

## Hallucinatory Task & Empty PR Directives
- **Zero-Diff Task Termination**: If the requested optimization, refactor, or fix is ALREADY natively present in the target branch, DO NOT create an empty pull request or commit an acknowledgment PR. Exit the task cleanly without opening a PR.
- **Stale Suggestion Guard**: Always verify the current code on `main`/`master` before planning changes. If no actionable diff is required, cancel task execution immediately.

## 2025-02-23 - Optimize Slotting Inner Loop
**Learning:** In optimization loops (like the slotting algorithm in `app/main.py`), repeatedly iterating over items that have already been matched leads to worst-case $O(N^2)$ behavior. Simply skipping over elements via `if target in matched_set: continue` is not sufficient for large inputs because traversing the list itself still takes $O(N)$.
**Action:** For loops that frequently skip processed items, periodically filter the source list (e.g., using list comprehension) to permanently remove matched items. This pattern reduced execution time by 90%+ in the slotting route.
## 2024-09-09 - Caching Datetime Parsing in Python Batch Processes
**Learning:** Python's `datetime.fromisoformat` and time-zone normalizations are significant CPU bottlenecks when parsing large JSON datasets containing duplicate/repeated string timestamps (common in order/dispatch data). In `app/main.py`'s slotting optimization, this accounted for a large portion of execution time.
**Action:** Always consider memoizing/caching string-to-datetime conversions in a simple dictionary mapping string inputs to their resulting objects or mathematical values when iterating over large lists with redundant dates.

## 2023-10-25 - [ISO String Parsing Overhead]
**Learning:** In highly iterated loops (e.g., `detect_anomalies`), utilizing `datetime.fromisoformat()` for standard ISO 8601 strings causes significant object allocation and validation overhead, creating a hidden performance bottleneck.
**Action:** When strictly standard date formats are guaranteed or easily validatable in a large loop, utilize string slicing (e.g., `entry[:10]` for dates) coupled with a fallback `try-except` block for robust edge-case handling.

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

## 2023-11-09 - Iteration and Parsing Overhead in Yield Optimizer
**Learning:** In the `optimize_yield` batch process, redundant calls to `datetime.fromisoformat` for lots with the same expiration date create significant CPU overhead. Additionally, sequentially scanning all rules for every lot when only the rule with the highest markdown percentage is needed leads to inefficient O(L * R) time complexity.
**Action:** Cache datetime parsing results (including failures) to avoid re-parsing duplicate timestamp strings. Pre-sort rules descending by target criteria (e.g., markdown percentage) to allow early exits from inner search loops, turning worst-case O(L * R) to O(L + R log R).

## 2023-10-24 - Dynamic Inner Loop Culling using Monotonic Outer Loop Data
**Learning:** When optimizing O(N^2) nested loops (e.g., in matching or slotting algorithms), we can utilize the monotonic properties of sorted outer lists to safely and dynamically cull the inner loop's search space during periodic cleanups. Since the outer list iterates in a guaranteed descending order, any inner loop target that violates the target matching requirement (e.g. `target_val < current_val`) will inherently violate it for all future outer loop iterations, allowing us to permanently drop it from the search space early and significantly decrease iterations.
**Action:** Always verify if nested iterative matches in FastAPI have sorted outer loops where the inner matching conditions rely on monotonic values, and aggressively cull those targets during scheduled periodic garbage collection cleanups to reduce processing times.

## 2024-05-15 - Replace list.remove() with list slicing
**Learning:** In sequential consumption loops like `app/labor_scheduler.py`'s `predict_schedule`, using `list.remove()` repeatedly causes O(N^2) time complexity because each removal shifts the remaining elements.
**Action:** Replace sequential `.remove()` calls with a single O(1) list slice operation (e.g. `list = list[used_count:]`) when items are consumed from the beginning of the list.

## 2024-05-16 - Optimize Resource Assignment with Index Pointers
**Learning:** Using `list.remove()` or even list slicing inside nested loops for sequential resource consumption can cause O(N^2) complexity or unnecessary memory allocations.
**Action:** Use an index pointer (e.g., `op_idx = 0`) that persists across the outer loop to track consumption from a sorted list, avoiding list mutations entirely and achieving true O(N) time complexity.
