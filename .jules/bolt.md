## 2023-10-27 - O(N*M) Surplus Iteration Bottleneck
**Learning:** In the inventory rebalance optimizer, finding the correct surplus location for a given deficit iterating over a global array of surpluses results in an O(N*M) bottleneck, bringing performance to ~50s on moderate inputs.
**Action:** Replace nested loops filtering data by SKU and Warehouse ID with pre-computed hash maps (surplus_lookup and surpluses_by_sku) initialized in the initial array traversal.
