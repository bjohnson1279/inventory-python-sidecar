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
## 2024-10-24 - Avoid converting to naive datetime objects for comparison
**Learning:** In `app/main.py`, converting ISO datetime strings to naive `datetime` objects via `d_date.astimezone(None).replace(tzinfo=None)` in a loop creates significant performance overhead due to the repeated underlying system timezone lookups.
**Action:** When comparing datetimes, always use timezone-aware UTC objects by initializing the current time with `datetime.now(timezone.utc)` and standardizing incoming parsed dates with `.replace(tzinfo=timezone.utc)` if they lack timezone info.
