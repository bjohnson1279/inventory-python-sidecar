# Inventory AI Sidecar - API Specification & Endpoint Reference

This document provides a comprehensive reference for all HTTP endpoints exposed by the Inventory AI Sidecar service.

---

## Authentication & Security Headers

### Authentication
Protected endpoints require authentication via the `X-API-Key` HTTP header.
- **Header Name**: `X-API-Key`
- **Validation**: Compared against the server's `INVENTORY_API_KEY` environment variable in constant time (`secrets.compare_digest`).
- **Exemptions**: Public health checks (`/health`, `/api/health`) and OpenAPI documentation endpoints (`/docs`, `/openapi.json`) do not require authentication.
- **Failure Responses**:
  - `403 Forbidden`: Returned when the header is missing or does not match the configured key.
  - `500 Internal Server Error`: Returned if `INVENTORY_API_KEY` is unconfigured in production environments.

### Rate Limiting
- **Window & Limit**: 100 requests per 60-second sliding window per client IP address.
- **Rejection**: Exceeding the rate limit returns `HTTP 429 Too Many Requests` with a `Retry-After: 60` response header.

### Security Headers
All responses include security headers enforced by `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'`
- `Cache-Control: no-store`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`

---

## Endpoint Catalog

1. [`GET /health`](#1-get-health)
2. [`GET /api/health`](#2-get-apihealth)
3. [`POST /optimize`](#3-post-optimize)
4. [`POST /anomaly-detect`](#4-post-anomaly-detect)
5. [`POST /copilot/query`](#5-post-copilotquery)
6. [`POST /cv/analyze-inbound`](#6-post-cvanalyze-inbound)
7. [`POST /simulate-warehouse`](#7-post-simulate-warehouse)
8. [`GET /calculate-emissions`](#8-get-calculate-emissions)
9. [`POST /labor/predict-schedule`](#9-post-laborpredict-schedule)
10. [`POST /rebalance-optimize`](#10-post-rebalance-optimize)
11. [`POST /pricing/optimize-yield`](#11-post-pricingoptimize-yield)

---

### 1. `GET /health`

Liveness and readiness probe endpoint for container orchestration systems (Kubernetes, AWS ECS) and load balancers.

- **HTTP Method**: `GET`
- **Route Path**: `/health`
- **Headers**:
  - `X-API-Key`: *(Optional / Public)* Not required.
- **Query / Path Parameters**: None.
- **Request Body**: None.
- **Response**:
  - **Status**: `200 OK`
  - **Content-Type**: `application/json`
  - **Schema**:
    ```json
    {
      "status": "ok",
      "service": "inventory-python-sidecar"
    }
    ```
- **Real-World Workflow**: Invoked every 5–10 seconds by ingress controllers or container runtimes to verify service health before routing incoming warehouse traffic.

---

### 2. `GET /api/health`

Alternative prefixed health check endpoint adhering to standard `/api` route conventions.

- **HTTP Method**: `GET`
- **Route Path**: `/api/health`
- **Headers**:
  - `X-API-Key`: *(Optional / Public)* Not required.
- **Query / Path Parameters**: None.
- **Request Body**: None.
- **Response**:
  - **Status**: `200 OK`
  - **Content-Type**: `application/json`
  - **Schema**:
    ```json
    {
      "status": "ok",
      "service": "inventory-python-sidecar"
    }
    ```
- **Real-World Workflow**: Used by API gateways and external monitoring dashboards where path prefixes are standardized to `/api/*`.

---

### 3. `POST /optimize`

Computes 3D Manhattan distances from storage locations to warehouse dispatch origin `(0, 0, 0)`, calculates SKU velocity with exponential time decay, and determines location swaps that maximize travel savings.

- **HTTP Method**: `POST`
- **Route Path**: `/optimize`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`OptimizeRequest`):
    - `locations` *(Array of LocationInput, Required)*: Maximum 10,000 items.
      - `id` *(String, Required)*: Unique location identifier (max 255 chars).
      - `grid_x` *(Integer, Required)*: X-coordinate in warehouse grid (-100,000 to 100,000).
      - `grid_y` *(Integer, Required)*: Y-coordinate in warehouse grid (-100,000 to 100,000).
      - `grid_z` *(Integer, Optional, Default: 0)*: Z-coordinate/tier level (-100,000 to 100,000).
    - `inventory` *(Array of InventoryInput, Required)*: Maximum 10,000 items.
      - `sku` *(String, Required)*: Stock keeping unit code (max 255 chars).
      - `location_id` *(String, Required)*: Current assigned location ID (max 255 chars).
    - `dispatches` *(Array of DispatchInput, Required)*: Maximum 10,000 items.
      - `sku` *(String, Required)*: SKU code (max 255 chars).
      - `location_id` *(String, Required)*: Dispatch origin location ID (max 255 chars).
      - `quantity` *(Integer, Required)*: Units dispatched (0 to 1,000,000).
      - `date` *(String, Required)*: ISO 8601 timestamp string (e.g., `"2026-03-15T08:30:00Z"`).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`List[SlottingSuggestion]`):
    - Array of suggestions sorted by `estimatedSavings` descending:
      - `sku` *(String)*: Target SKU identifier.
      - `currentLocationId` *(String)*: Existing bin/location ID.
      - `currentDistance` *(Float)*: 3D Manhattan distance from origin.
      - `currentVelocity` *(Float)*: Time-decayed dispatch velocity.
      - `recommendedLocationId` *(String)*: Suggested target location ID.
      - `recommendedDistance` *(Float)*: Distance of recommended location.
      - `potentialSwapSku` *(String or null)*: SKU currently occupying target location, if any.
      - `estimatedSavings` *(Float)*: Estimated picker travel distance saved.
- **Real-World Workflow**: Executed weekly or post-promotional wave by Warehouse Management Systems (WMS) to re-slot fast-moving inventory closer to packing stations.

---

### 4. `POST /anomaly-detect`

Performs multi-vector anomaly detection across inventory ledger entries, cycle counts, and high-frequency scan events using statistical heuristics (Z-score, IQR) and Scikit-Learn `IsolationForest`.

- **HTTP Method**: `POST`
- **Route Path**: `/anomaly-detect`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`AnomalyDetectRequest`):
    - `ledger_entries` *(Array of LedgerEntryInput, Required)*: Up to 10,000 items.
      - `sku` *(String, Required)*: SKU identifier (max 255 chars).
      - `location_id` *(String, Required)*: Location ID (max 255 chars).
      - `quantity` *(Integer, Required)*: Adjustment quantity (-1,000,000 to 1,000,000).
      - `reason` *(String, Required)*: Reason code (e.g., `"shrinkage"`, `"damage"`, `"write-off"`).
      - `actor_id` *(String, Required)*: Operator identifier (max 255 chars).
      - `occurred_at` *(String, Required)*: ISO 8601 timestamp.
      - `reference_id` *(String, Optional)*: External audit or transaction reference.
    - `cycle_counts` *(Array of CycleCountInput, Required)*: Up to 10,000 items.
      - `sku` *(String, Required)*: SKU identifier.
      - `location_id` *(String, Required)*: Location identifier.
      - `expected_quantity` *(Integer, Required)*: Expected on-hand units (0 to 1,000,000).
      - `counted_quantity` *(Integer, Required)*: Physically counted units (0 to 1,000,000).
      - `counted_at` *(String, Required)*: ISO 8601 timestamp.
      - `actor_id` *(String, Required)*: Auditor/operator ID.
    - `scan_events` *(Array of ScanEventInput, Required)*: Up to 10,000 items.
      - `sku` *(String, Required)*: SKU identifier.
      - `location_id` *(String, Required)*: Location identifier.
      - `scan_context` *(String, Required)*: Scan event context/station (max 1,000 chars).
      - `scanned_at` *(String, Required)*: ISO 8601 timestamp.
      - `actor_id` *(String, Required)*: Scanner operator ID.
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`AnomalyDetectResponse`):
    - `alerts` *(Array of AnomalyAlert)*:
      - `alert_type` *(String)*: Category (`"UNUSUAL_ADJUSTMENT"`, `"CYCLE_COUNT_DISCREPANCY"`, `"AFTER_HOURS_BURST"`, `"HIGH_RISK_ACTOR"`).
      - `severity` *(String)*: `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, or `"LOW"`.
      - `confidence` *(Float)*: Confidence score between 0.0 and 1.0.
      - `sku` *(String or null)*: Associated SKU.
      - `location_id` *(String or null)*: Associated location.
      - `actor_id` *(String or null)*: Associated actor.
      - `title` *(String)*: Human-readable alert summary.
      - `description` *(String)*: Diagnostic explanation.
      - `evidence` *(Object)*: Quantitative statistical evidence.
      - `detected_at` *(String)*: UTC timestamp of detection.
    - `summary` *(Object)*:
      - `total_alerts` *(Integer)*: Total count of alerts generated.
      - `high_severity_count` *(Integer)*: Number of CRITICAL or HIGH alerts.
      - `average_confidence` *(Float)*: Mean confidence score across alerts.
- **Real-World Workflow**: Scheduled nightly or triggered after inventory cycle counts to flag theft, phantom inventory, or employee scanning anomalies for warehouse loss prevention teams.

---

### 5. `POST /copilot/query`

Natural language query engine that classifies inventory operational intent, extracts relevant metrics, and produces actionable operational suggestions.

- **HTTP Method**: `POST`
- **Route Path**: `/copilot/query`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`CopilotRequest`):
    - `query` *(String, Required)*: Natural language question or command (max 1,000 characters).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`CopilotResponse`):
    - `query` *(String)*: Sanitized query echo.
    - `intent` *(String)*: Classified intent category (`"STOCKOUT_RISK_ANALYSIS"`, `"SHRINKAGE_ANOMALY_QUERY"`, `"GENERAL_INVENTORY_QUERY"`).
    - `insights` *(String)*: Natural language diagnostic summary.
    - `metricData` *(Object)*: Domain metrics relevant to the classified intent.
    - `suggestedActions` *(Array of Strings)*: Recommended next steps.
- **Real-World Workflow**: Integrated into warehouse management web apps and mobile terminals, allowing floor managers to ask questions such as "What SKUs are at risk of stockout?" or "Investigate shrinkage in aisle 4".

---

### 6. `POST /cv/analyze-inbound`

Computer vision payload ingestion gateway. Validates base64 camera frame payloads, performs simulated OCR text extraction, dimension estimation, and anomaly/damage detection.

- **HTTP Method**: `POST`
- **Route Path**: `/cv/analyze-inbound`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`AnalyzeInboundRequest`):
    - `image_base64` *(String, Required)*: Base64-encoded image string (max 5,000,000 characters). Must be valid base64.
    - `po_id` *(String, Optional)*: Purchase order identifier for context (max 255 characters).
- **Response**:
  - **Status**: `200 OK` (or `400 Bad Request` if base64 decoding fails).
  - **Schema** (`AnalyzeInboundResponse`):
    - `dimensions` *(Object)*:
      - `length` *(Float)*: Measured package length (cm).
      - `width` *(Float)*: Measured package width (cm).
      - `height` *(Float)*: Measured package height (cm).
    - `ocr_text` *(String)*: Extracted barcode or supplier text.
    - `anomaly_score` *(Float)*: Packaging defect or damage score (0.0 to 1.0).
    - `has_damage` *(Boolean)*: `true` if damage is detected (`anomaly_score > 0.75`).
- **Real-World Workflow**: Invoked by inbound receiving dock conveyor cameras as pallets or cartons pass through automated inspection tunnels.

---

### 7. `POST /simulate-warehouse`

Discrete-event digital twin simulator modeling order wave processing, picker allocation, throughput rates, and bottleneck identification.

- **HTTP Method**: `POST`
- **Route Path**: `/simulate-warehouse`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`SimulationRequest`):
    - `warehouse_id` *(String, Optional, Default: `"WH-MAIN"`)*: Target warehouse code (max 50 chars, alphanumeric with dashes/underscores).
    - `order_wave_count` *(Integer, Optional, Default: 10)*: Number of order waves to simulate (1 to 1,000).
    - `active_pickers_count` *(Integer, Optional, Default: 5)*: Number of active picking staff (1 to 10,000).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`SimulationResponse`):
    - `scenario_id` *(String)*: Generated scenario run identifier.
    - `duration_seconds` *(Integer)*: Simulated operational window in seconds (e.g., 3600).
    - `total_orders_processed` *(Integer)*: Total orders simulated across waves.
    - `average_fulfillment_time_minutes` *(Float)*: Average time to complete an order wave.
    - `bottleneck_bin_id` *(String)*: Location identifier with the highest congestion.
    - `throughput_per_hour` *(Float)*: Projected orders completed per hour.
    - `picker_utilization_rate` *(Float)*: Resource efficiency ratio (0.0 to 1.0).
    - `congestion_hotspots` *(Array of Strings)*: Aisle or rack zones experiencing congestion.
- **Real-World Workflow**: Used by operations planning teams during peak season prep (e.g., Prime Day, Black Friday) to forecast required staffing levels and prevent bottlenecks.

---

### 8. `GET /calculate-emissions`

Calculates logistics and facility greenhouse gas emissions (Scope 1 and Scope 3 CO2e) for sustainability compliance and ESG reporting.

- **HTTP Method**: `GET`
- **Route Path**: `/calculate-emissions`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query Parameters**:
  - `tenant_id` *(String, Optional, Default: `"tenant-1"`)*: Organization tenant identifier (max 50 chars, alphanumeric with dashes/underscores).
  - `period` *(String, Optional, Default: `"2026-Q3"`)*: Calendar quarter in `YYYY-Q[1-4]` format (max 20 chars).
- **Request Body**: None.
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`EsgReportResponse`):
    - `tenant_id` *(String)*: Evaluated tenant identifier.
    - `period` *(String)*: Evaluated reporting quarter.
    - `transport_emissions_co2e_kg` *(Float)*: Freight logistics emissions in kg CO2e.
    - `facility_emissions_co2e_kg` *(Float)*: Facility power/heating emissions in kg CO2e.
    - `total_emissions_co2e_kg` *(Float)*: Aggregate emissions in kg CO2e.
    - `emissions_intensity_per_order` *(Float)*: Average kg CO2e per fulfilled order.
    - `breakdown_by_mode` *(Object)*: Mapping of transit mode to emissions (`"air"`, `"groundExpress"`, `"ltl"`).
- **Real-World Workflow**: Polled on a monthly or quarterly schedule by corporate sustainability dashboards to generate carbon accounting disclosures.

---

### 9. `POST /labor/predict-schedule`

Evaluates forecasted pick demand across warehouse zones against operator historical pick rates to generate optimal shift assignments.

- **HTTP Method**: `POST`
- **Route Path**: `/labor/predict-schedule`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`PredictScheduleRequest`):
    - `operators` *(Array of OperatorInput, Required)*: Up to 10,000 operators.
      - `operator_id` *(String, Required)*: Unique worker identifier (max 255 chars).
      - `average_picks_per_hour` *(Float, Required)*: Historical pick efficiency (0.0 to 1,000,000.0).
    - `demand_forecasts` *(Array of DemandInput, Required)*: Up to 10,000 demand windows.
      - `zone` *(String, Required)*: Warehouse zone name (max 255 chars).
      - `forecasted_quantity` *(Integer, Required)*: Expected units to pick (0 to 1,000,000).
      - `period_start` *(String, Required)*: Shift start timestamp (ISO 8601).
      - `period_end` *(String, Required)*: Shift end timestamp (ISO 8601).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`List[ShiftSuggestion]`):
    - Array of shift assignments:
      - `operator_id` *(String)*: Assigned operator.
      - `shift_start` *(String)*: Shift start timestamp.
      - `shift_end` *(String)*: Shift end timestamp.
      - `assigned_zone` *(String)*: Target warehouse zone.
      - `predicted_demand` *(Integer)*: Pick units assigned to this shift.
- **Real-World Workflow**: Run daily by shift supervisors to staff zones based on expected picking volume, prioritizing high-velocity pickers for high-volume demand windows.

---

### 10. `POST /rebalance-optimize`

Computes optimal inter-facility stock transfers to rebalance inventory across warehouses, resolving deficit stockouts while minimizing transportation penalties and transit times.

- **HTTP Method**: `POST`
- **Route Path**: `/rebalance-optimize`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`RebalanceRequest`):
    - `warehouses` *(Array of WarehouseInput, Required)*: Facility definitions.
      - `id` *(String, Required)*: Warehouse code (max 255 chars).
      - `name` *(String, Required)*: Warehouse display name.
      - `region` *(String, Optional)*: Geographic region code.
    - `stock_levels` *(Array of StockLevelInput, Required)*: Current stock positions.
      - `sku` *(String, Required)*: SKU code.
      - `warehouse_id` *(String, Required)*: Facility ID.
      - `on_hand` *(Integer, Required)*: Available physical units (0 to 1,000,000).
      - `allocated` *(Integer, Optional, Default: 0)*: Units reserved for orders (0 to 1,000,000).
      - `in_transit` *(Integer, Optional, Default: 0)*: Units incoming (0 to 1,000,000).
      - `safety_stock` *(Integer, Optional, Default: 0)*: Buffer threshold (0 to 1,000,000).
    - `demand_forecasts` *(Array of DemandForecastInput, Required)*: Velocity forecasts.
      - `sku` *(String, Required)*: SKU code.
      - `warehouse_id` *(String, Required)*: Facility ID.
      - `daily_velocity_7d` *(Float, Optional, Default: 0.0)*: 7-day daily velocity.
      - `daily_velocity_30d` *(Float, Optional, Default: 0.0)*: 30-day daily velocity.
      - `daily_velocity_90d` *(Float, Optional, Default: 0.0)*: 90-day daily velocity.
    - `lead_times` *(Array of LeadTimeInput, Required)*: Inter-facility transit lead times.
      - `source_warehouse_id` *(String, Required)*: Origin facility.
      - `dest_warehouse_id` *(String, Required)*: Destination facility.
      - `transit_days` *(Integer, Required)*: Transit duration in days (0 to 10,000).
    - `shipping_costs` *(Array of ShippingCostInput, Required)*: Freight costs.
      - `source_warehouse_id` *(String, Required)*: Origin facility.
      - `dest_warehouse_id` *(String, Required)*: Destination facility.
      - `cost_per_unit` *(Float, Required)*: Shipping cost per unit (0.0 to 1,000,000.0).
    - `constraints` *(Object, Optional)*:
      - `max_transfers_per_run` *(Integer, Default: 20)*: Transfer limit (1 to 1,000,000).
      - `min_transfer_quantity` *(Integer, Default: 5)*: Minimum batch size (1 to 1,000,000).
      - `min_days_of_cover_target` *(Float, Default: 14.0)*: Target Days of Cover (DoC).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`RebalanceMatrix`):
    - `recommendations` *(Array of RebalanceRecommendation)*:
      - `sku` *(String)*: SKU to transfer.
      - `source_warehouse_id` *(String)*: Origin facility.
      - `dest_warehouse_id` *(String)*: Destination facility.
      - `quantity` *(Integer)*: Transfer quantity.
      - `priority` *(String)*: `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, or `"LOW"`.
      - `estimated_shipping_cost` *(Float)*: Estimated freight expense.
      - `source_current_doc` *(Float)*: Origin current Days of Cover.
      - `dest_current_doc` *(Float)*: Destination current Days of Cover.
      - `source_projected_doc` *(Float)*: Origin projected Days of Cover post-transfer.
      - `dest_projected_doc` *(Float)*: Destination projected Days of Cover post-transfer.
      - `urgency_reason` *(String)*: Rationale for transfer priority.
    - `matrix` *(Object)*: Source-destination transfer volume matrix.
    - `summary` *(Object)*: Aggregate statistics (`total_transfers`, `total_cost`, `skus_improved`, `avg_doc_improvement`).
- **Real-World Workflow**: Executed daily or bi-weekly by multi-echelon inventory planning engines to trigger inter-warehouse transfer orders.

---

### 11. `POST /pricing/optimize-yield`

Evaluates perishable lot-level inventory using First Expired, First Out (FEFO) rules against tiered liquidation rules to recommend price markdowns.

- **HTTP Method**: `POST`
- **Route Path**: `/pricing/optimize-yield`
- **Headers**:
  - `X-API-Key`: *(Required)* Active microservice API key.
- **Query / Path Parameters**: None.
- **Request Body**:
  - **Content-Type**: `application/json`
  - **Schema** (`OptimizeYieldRequest`):
    - `rules` *(Array of LiquidationRuleInput, Required)*: Markdown policies (max 10,000).
      - `rule_id` *(String, Required)*: Rule identifier (max 255 chars).
      - `days_to_expiration` *(Integer, Required)*: Threshold days remaining (0 to 1,000,000).
      - `markdown_percentage` *(Float, Required)*: Price discount percent (0.0 to 100.0).
      - `department` *(String, Optional)*: Target department filter (e.g., `"Produce"`).
      - `sku` *(String, Optional)*: Target SKU filter.
    - `lots` *(Array of LotInput, Required)*: Perishable inventory lots (max 10,000).
      - `variant_id` *(String, Required)*: Unique lot/variant ID (max 255 chars).
      - `sku` *(String, Required)*: SKU code (max 255 chars).
      - `department` *(String, Required)*: Department name (max 255 chars).
      - `current_price_cents` *(Integer, Required)*: Current unit price in cents (0 to 100,000,000).
      - `expiration_date` *(String, Required)*: Expiration date in ISO format (e.g., `"2026-04-10"`).
- **Response**:
  - **Status**: `200 OK`
  - **Schema** (`List[MarkdownSuggestion]`):
    - Array of markdown suggestions:
      - `variant_id` *(String)*: Lot identifier.
      - `rule_id` *(String)*: Applied liquidation rule.
      - `original_price_cents` *(Integer)*: Starting price in cents.
      - `suggested_price_cents` *(Integer)*: Suggested discounted price in cents.
      - `reason` *(String)*: Human-readable markdown explanation with days until expiration.
- **Real-World Workflow**: Triggered daily by grocery and perishable fulfillment ERPs to apply automated clearance pricing before stock reaches unrecoverable spoil dates.
