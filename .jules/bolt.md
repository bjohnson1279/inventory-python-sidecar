## 2026-09-11 - Thread Contention in FastApi synchronous handlers
**Learning:** Adding multiprocessing parameters like `n_jobs=-1` to Scikit-Learn algorithms (e.g. `IsolationForest`) inside synchronous API request handlers might degrade performance due to severe thread contention under load.
**Action:** Avoid blindly optimizing model fitting with `n_jobs=-1` inside synchronous endpoint handlers; measure concurrent load performance first or offload heavy compute to an asynchronous task queue.
