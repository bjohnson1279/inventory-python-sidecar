# Inventory AI Sidecar

An AI-driven FastAPI sidecar microservice providing high-performance warehouse inventory optimization, anomaly detection, copilot natural language query processing, digital twin simulation, ESG carbon emissions tracking, labor scheduling heuristics, multi-warehouse rebalancing, and dynamic FEFO yield optimization.

---

## Architecture & Features

The sidecar acts as an auxiliary computational engine for core warehouse and inventory management systems:

- **Warehouse Slotting Optimization (`POST /optimize`)**: Computes 3D Manhattan distances to warehouse origin, evaluates SKU dispatch velocities with exponential time-decay weighting, and recommends optimal location swaps to minimize travel distance.
- **Ledger Anomaly Detection (`POST /anomaly-detect`)**: Leverages Scikit-Learn `IsolationForest` unsupervised machine learning and statistical heuristics across ledger shrinkage, cycle counts, and high-frequency scan events.
- **AI Copilot Query (`POST /copilot/query`)**: Natural language query router analyzing inventory intent (e.g., stockout risks, velocity trends, rebalance recommendations).
- **Inbound Computer Vision Gateway (`POST /cv/analyze-inbound`)**: Decodes and inspects base64 camera frame payloads for inbound SKU defect and barcode validation.
- **Digital Twin Simulation (`POST /simulate-warehouse`)**: Simulates warehouse order wave fulfillment rates, picker utilization, and bottleneck detection across varied active picker counts.
- **ESG Carbon Emissions Calculator (`GET /calculate-emissions`)**: Quantifies freight logistics carbon emissions (kg CO2e) by transit mode (road, rail, air, maritime).
- **Labor Shift Scheduler (`POST /labor/predict-schedule`)**: Evaluates forward demand forecasts against operator pick velocities to suggest scheduled labor shifts.
- **Inventory Rebalance Optimizer (`POST /rebalance-optimize`)**: Optimizes stock redistribution between surplus and deficit warehouses while respecting shipping costs, transit lead times, and capacity constraints.
- **Yield & Markdown Optimizer (`POST /pricing/optimize-yield`)**: Evaluates lot-level FEFO (First Expired, First Out) expiration proximity against tiered markdown rules to maximize revenue recovery.

---

## Prerequisites

- **Python**: Version 3.11 or 3.12
- **Virtual Environment**: `venv` or `pyenv`
- **Docker** (optional): For containerized deployments

---

## Installation & Setup

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repository_url>
   cd inventory-python-sidecar
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   pip install pytest httpx
   ```

4. **Environment Variables Configuration:**
   Configure the required environment variables:
   - `INVENTORY_API_KEY`: Secret string required to authenticate requests to protected endpoints via the `X-API-Key` HTTP header.
   - `APP_ENV` *(Optional)*: Set to `test` or `testing` during test runs (defaults to `test_key` if `APP_ENV=test` or when executed under `pytest`).

   Example:
   ```bash
   export INVENTORY_API_KEY="your-secure-api-key"
   ```

---

## Running the Application

### Local Development Server

Run the service with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
```

Interactive OpenAPI documentation is available locally at:
- **Swagger UI**: [http://localhost:5000/docs](http://localhost:5000/docs)
- **ReDoc**: [http://localhost:5000/redoc](http://localhost:5000/redoc)
- **OpenAPI Schema**: [http://localhost:5000/openapi.json](http://localhost:5000/openapi.json)

### Running with Docker

Build and run using Docker:

```bash
docker build -t inventory-ai-sidecar:latest .
docker run -p 5000:5000 inventory-ai-sidecar:latest
```

---

## Running Tests

Execute the automated test suite with `pytest`:

```bash
# Run all tests
python -m pytest

# Run specific sidecar integration tests
python -m pytest app/tests/test_sidecar.py

# Run rebalance boundary test suite
python -m pytest app/tests/test_rebalance_bounds.py
```

---

## Security & Middleware Architecture

- **API Key Authentication**: Protected endpoints enforce authentication via the `X-API-Key` header validated using constant-time comparison against `INVENTORY_API_KEY`. Public endpoints (`/health`, `/api/health`, `/docs`, `/openapi.json`) are exempted.
- **Security Headers Middleware**: Enforces defense-in-depth HTTP headers (`Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Permissions-Policy`, `Cache-Control`, `Referrer-Policy`) across all endpoints.
- **In-Memory Rate Limiting**: Token-bucket / sliding window rate limiter allowing up to 100 requests per 60-second window per client IP, returning `429 Too Many Requests` with a `Retry-After` header when triggered.
- **CORS Protection**: Whitelists trusted origin `https://inventory-ai.internal`.
- **Input Validation**: Pydantic v2 schemas enforce strict length (`max_length`), list size bounds, and numerical constraints (`ge`, `le`) across all payload models to prevent DoS attacks.

---

## API Endpoint Reference

All protected endpoints require the `X-API-Key` request header matching the configured `INVENTORY_API_KEY`. Health check routes and OpenAPI schema routes are public.

| Route | Method | Headers | Parameters | Request Body | Response (200 OK) | Description & Use Case |
|---|---|---|---|---|---|---|
| `/health` | `GET` | None *(Public)* | None | None | `{"status": "ok", "service": "str"}` | Liveness / readiness health check for container orchestration and load balancers. |
| `/api/health` | `GET` | None *(Public)* | None | None | `{"status": "ok", "service": "str"}` | Alternative prefixed health check endpoint. |
| `/optimize` | `POST` | `X-API-Key` *(Required)* | None | `OptimizeRequest` (`locations`, `inventory`, `dispatches`) | `List[SlottingSuggestion]` | Optimizes SKU storage slotting to minimize picker travel distance based on historical dispatch velocity. |
| `/anomaly-detect` | `POST` | `X-API-Key` *(Required)* | None | `AnomalyDetectRequest` (`ledger_entries`, `cycle_counts`, `scan_events`) | `AnomalyDetectResponse` (`anomalies_detected`, `alerts`, `overall_risk_score`) | Detects shrinkage, theft, and scan frequency anomalies across inventory movements using Isolation Forest. |
| `/copilot/query` | `POST` | `X-API-Key` *(Required)* | None | `CopilotRequest` (`query`) | `CopilotResponse` (`query`, `intent`, `insights`, `metricData`, `suggestedActions`) | Natural language query interface returning structured inventory insights and recommended workflows. |
| `/cv/analyze-inbound` | `POST` | `X-API-Key` *(Required)* | None | `AnalyzeInboundRequest` (`image_base64`, `po_id` *(Optional)*) | `AnalyzeInboundResponse` (`dimensions`, `ocr_text`, `anomaly_score`, `has_damage`) | Validates inbound freight condition and extracts OCR text from camera capture feeds. |
| `/simulate-warehouse` | `POST` | `X-API-Key` *(Required)* | None | `SimulationRequest` (`warehouse_id`, `order_wave_count`, `active_pickers_count`) | `SimulationResponse` (`scenario_id`, `duration_seconds`, `total_orders_processed`, `average_fulfillment_time_minutes`, `bottleneck_bin_id`, `throughput_per_hour`, `picker_utilization_rate`, `congestion_hotspots`) | Simulates picking throughput and wave cycle times for capacity planning. |
| `/calculate-emissions` | `GET` | `X-API-Key` *(Required)* | `tenant_id` *(Optional)*, `period` *(Optional)* | None | `EsgReportResponse` (`tenant_id`, `period`, `transport_emissions_co2e_kg`, `facility_emissions_co2e_kg`, `total_emissions_co2e_kg`, `emissions_intensity_per_order`, `breakdown_by_mode`) | Computes freight transport carbon emissions breakdown for sustainability reporting. |
| `/labor/predict-schedule` | `POST` | `X-API-Key` *(Required)* | None | `PredictScheduleRequest` (`demand_forecasts`, `operators`) | `List[ShiftSuggestion]` | Schedules picker workforce shifts based on forecast demand waves. |
| `/rebalance-optimize` | `POST` | `X-API-Key` *(Required)* | None | `RebalanceRequest` (`warehouses`, `stock_levels`, `demand_forecasts`, `lead_times`, `shipping_costs`, `constraints`) | `RebalanceMatrix` (`recommendations`, `total_cost`, `total_units_transferred`) | Calculates optimal inter-warehouse inventory transfers to resolve localized stockouts. |
| `/pricing/optimize-yield` | `POST` | `X-API-Key` *(Required)* | None | `OptimizeYieldRequest` (`rules`, `lots`) | `List[MarkdownSuggestion]` | Generates FEFO-based markdown pricing suggestions for expiring perishable stock. |
