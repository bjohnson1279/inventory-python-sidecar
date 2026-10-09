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

## 2024-05-24 - Efficient List Rotations and Parsing Caching
**Learning:** Sequential consumption/removal of items from a list inside a loop using `list.remove()` causes algorithmic complexity to drop to O(N²), causing serious bottlenecking for larger processing volumes. Also, repetitive datetime parsing (`datetime.fromisoformat`) for identical date strings acts as a significant overhead point in inner loops.
**Action:** Always slice lists `list = list[used_count:]` or use indexing for O(1) bulk removals when iterating in greedy algorithms. Additionally, apply dictionary-based caching (memoization) to string-to-datetime conversions for recurring data sets to drastically reduce parse time.
## 2025-02-23 - Avoid List Slicing in Greedy Consumption Loops
**Learning:** Using list slicing (e.g. `list = list[used:]`) to consume elements within a loop allocates a new list every iteration, leading to O(M*N) time complexity and unnecessary memory overhead.
**Action:** When sequentially consuming items from a list within a loop, use an index pointer (e.g., `op_idx = 0`) that persists across the outer loop to achieve true O(N) complexity without mutating the list or allocating new ones.
## 2024-05-15 - Cache O(N) Rule Scanning in Yield Optimizer
**Learning:** The O(N) linear scan over sorted rules per lot in `optimize_yield` causes a severe performance bottleneck (O(M*N)) when dealing with many lots having the same department/sku/expiration attributes.
**Action:** Apply dictionary-based caching (memoization) using `(department, sku, days_until_exp)` as the key to convert repetitive O(N) scans into O(1) lookups. Ensure cache key creation is wrapped in a try/except block for `TypeError` to handle potential unhashable inputs.
## 2025-02-23 - Avoid Parsing Full Datetime when Only Days are Needed
**Learning:** Parsing full ISO 8601 strings with timezone information in tight loops is extremely expensive. When calculating only the number of days ago, caching on the full timestamp misses opportunities, and parsing the time component is redundant.
**Action:** Extract the date portion (first 10 characters) as the cache key and for `datetime.fromisoformat` parsing, reducing both cache misses and parsing overhead.

## 2023-11-20 - Pure Python Statistics for Small Datasets
**Learning:** In high-throughput synchronous inner loops processing small lists or datasets, using heavy array-based libraries like numpy for simple statistical operations (e.g., np.mean, np.std, np.percentile) introduces significant C-binding and object conversion overhead.
**Action:** Use pure Python implementations (like sum() for mean/variance or native sorting for percentiles) for simple statistical operations on small datasets to improve execution speed.

## 2026-09-29 - Pre-calculate Inner Loop Constants
**Learning:** In nested $O(N \times M)$ loops (e.g. matching algorithms), executing math operations like `int()`, `max()`, and multiplication on values that are constant relative to the inner loop iteration causes significant unnecessary CPU overhead.
**Action:** Always pre-calculate fixed values (like `target * max(vel, 0.01)`) in the outer loop or during the initial data structuring phase to avoid repeated identical math in inner loops.

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

## 2026-09-29 - Surgical Optimization Edits and No Scratch Script Commits
**Learning:** Running whole-file formatters or regenerating entire components while performing performance optimizations introduces massive whitespace/formatting diffs (1,000+ lines), masking the real optimization, invalidating git blame, and causing painful merge conflicts with concurrent PRs. Additionally, committing scratch benchmark or patch scripts (`patch_*.py`, `test.cjs`) pollutes production repositories and triggers CI guardrail failures.
**Action:** Restrict all algorithmic and performance optimizations to strictly scoped replacement chunks. Diff size must reflect only the functional optimization. Always clean up temporary benchmark or patch scripts with `git rm -f` before committing.
## 2026-10-27 - Pre-calculate Inner Loop Constants
**Learning:** In nested O(N * M) loops (e.g., matching or rebalance algorithms), performing redundant function calls like `max(val, 0.01)` and recalculating constants relative to the inner loop iteration causes significant unnecessary CPU overhead.
**Action:** Pre-calculate fixed values and hoist functions like `max()` out of inner loops, passing them through intermediate data structures (e.g. dictionaries) if necessary, to avoid repeated identical operations.

## Additive Documentation & Scratch Cleanliness Directives
- **Strictly Additive Journal Updates**: When updating `.jules/*.md`, strictly append new dated entries (`## YYYY-MM-DD - Title`). NEVER delete, truncate, or overwrite historical learnings or previous entries.
- **Substantive Code Diff Requirement**: Pull requests must include substantive code changes in `src/`, `app/`, `lib/`, or `tests/`. Never open PRs that modify only `.jules/*.md` journals or root scratch scripts.
- **Zero Scratch File Commits**: Never commit `*.diff`, `*.patch`, `test_*.ts`, `test_*.js`, `test.cjs`, `fix_*.php`, or `patch_*.py` files. Always remove temporary debugging or verification scripts prior to committing.

## Scope Quarantine, Journaling & Security Test Invariants
- **Strictly Append-Only Journaling**: When adding learnings to `.jules/*.md`, append strictly at the end of the file. Do not rewrite, deduplicate, or remove lines beginning with `## YYYY-MM-DD`.
- **Surgical Scope Quarantine**: Modify only the files directly involved in the issue and their corresponding test fixtures. Do not delete, rename, or perform drive-by cleanups of unrelated root-level scripts or legacy files.
- **Coupled Test Fixture Awareness for Security Invariants**: When changing fail-open fallback behavior (such as hardening decryption to fail closed), always update upstream test mocks that rely on plaintext credentials or mock values.
## 2024-05-25 - Pre-calculate Combined Dictionary Lookups in Nested Loops
**Learning:** When evaluating cost functions in nested O(N*M) loops requiring multiple dictionary lookups for the same key pair (e.g., `costs[(src, dest)]` and `lead_times[(src, dest)]`), performing independent lookups and recalculating the final penalty inside the inner loop adds significant redundant overhead.
**Action:** Compute a composite penalty cache (`combined_penalty_cache`) over the union of relevant keys before the loop. This reduces multiple dictionary accesses and mathematical operations per iteration into a single O(1) lookup.
## 2023-11-20 - Avoid Intermediate List Allocation in Aggregators
**Learning:** Using list comprehensions inside aggregators like `sum()` (e.g., `sum([x for x in list])`) eagerly allocates an intermediate list in memory before processing it. In large loops or web request handlers, this causes unnecessary O(n) spatial overhead, memory pressure, and garbage collection pauses.
**Action:** Always replace list comprehensions inside aggregators with generator expressions (e.g., `sum(x for x in list)`). This computes values lazily, requiring only O(1) additional space.

- **Centralize Shared Test Doubles for Abstract Domain Repositories**: When mocking domain repositories across multiple test suites, define a single shared test double rather than duplicating inline mocks to prevent cross-suite synchronization bugs.

## 2024-05-18 - Eager Evaluation in `dict.get()`
**Learning:** In Python, passing a dynamically calculated fallback value (e.g., `d.get("key", max(v))`) evaluates the calculation eagerly on *every* loop iteration, completely negating the intended caching/hoisting optimization and slowing down performance due to added dictionary overhead.
**Action:** When falling back to an expensive calculation during dictionary lookup, use conditional logic (`d["key"] if "key" in d else expensive_func()`) to guarantee lazy evaluation.

## 2024-05-25 - Consolidate Multiple Default Values in Composite Cache Lookups
**Learning:** When using a composite cache (e.g., storing a tuple of pre-calculated values for a key pair), extracting the fallback values using `.get(key, (default_val_1, default_val_2))` prevents independent evaluations. If the defaults were originally separate (e.g., `cost_pu = costs.get((s, d), 1.0)` and `penalty = combined_penalty_cache.get((s, d), 1.51)`), combining them into a single tuple lookup ensures efficient execution while maintaining precise default behavior.
**Action:** When migrating multiple dictionary lookups to a single composite dictionary lookup, accurately map the original independent default values to a single tuple fallback in the `.get()` call to preserve logical correctness and optimize performance.

## 2024-05-25 - Avoid Time Truncation in Date Differences
**Learning:** When attempting to optimize caching for date parsing (e.g., `datetime.fromisoformat`) by truncating ISO strings to their date component (`[:10]`), the time defaults to midnight (`00:00:00`). If the resulting datetime is later used in time-sensitive arithmetic (like `(exp_dt - now).days`), this truncation alters the absolute time difference, potentially causing logical regressions (e.g., evaluating a future expiration as already expired).
**Action:** Do not truncate the time component of datetime strings for caching purposes if the parsed datetime is used in sensitive interval or duration logic.

## 2024-05-25 - Pre-calculate Redundant Multipliers Outside Evaluation Loops
**Learning:** In optimization loops where a math operation involves constants relative to a specific entity (e.g., `(100.0 - best_rule.markdown_percentage) / 100.0` inside an inner loop evaluating lots), performing this math repeatedly creates unnecessary overhead.
**Action:** Pre-calculate these multipliers outside the loop, storing them in a cache dictionary (e.g., mapping `rule_id` to the precalculated multiplier) to replace redundant subtraction and division with an O(1) dictionary lookup.
