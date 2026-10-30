# Inventory AI Sidecar

An AI-powered FastAPI sidecar service providing warehouse inventory optimization, anomaly detection, copilot AI query processing, digital twin simulation, ESG emissions calculation, labor shift scheduling, inventory rebalancing, and yield optimization.

## Features & Services

- **Slotting Optimization (`/optimize`)**: Calculates warehouse distance optimization and SKU placement suggestions.
- **Anomaly Detection (`/anomaly-detect`)**: ML-driven anomaly detection on ledger entries using Isolation Forest.
- **Copilot Query (`/copilot/query`)**: Natural language query processing for stockout risks, velocity, and rebalance recommendations.
- **Computer Vision Gateway (`/analyze-inbound`)**: Analyzes camera frame metrics for inbound inventory processing.
- **Digital Twin Simulation (`/simulate-warehouse`)**: Simulates warehouse operations and picking throughput.
- **ESG Calculator (`/calculate-emissions`)**: Estimates carbon emissions by freight transport mode.
- **Labor Scheduler (`/predict-schedule`)**: Predicts required labor shifts based on historical demand trends.
- **Rebalance Optimizer (`/rebalance-optimize`)**: Optimizes multi-location inventory movement matrix.
- **Yield Optimizer (`/optimize-yield`)**: Generates actionable inventory markdown suggestions.

## Prerequisites

- Python 3.10+
- Virtual environment tool (`venv`)

## Installation & Setup

1. **Clone the repository and navigate into the project directory:**
   ```bash
   cd inventory-python-sidecar
   ```

2. **Set up a virtual environment and activate it:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

Start the FastAPI application locally using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running, interactive API documentation (Swagger UI) is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

Run the test suite using `pytest`:

```bash
pytest app/tests/test_sidecar.py
```

## API Endpoint Reference Summary

| Endpoint | Method | Description |
|---|---|---|
| `/health`, `/api/health` | GET | Health check endpoint returning service status. |
| `/optimize` | POST | Warehouse slotting optimization for SKUs and location grid. |
| `/anomaly-detect` | POST | Anomaly detection on inventory ledger entries. |
| `/copilot/query` | POST | Copilot AI query analysis and stockout risk insights. |
| `/analyze-inbound` | POST | Inbound visual quality assessment metrics. |
| `/simulate-warehouse` | POST | Digital twin simulation for warehouse picking operations. |
| `/calculate-emissions` | GET | Freight transport ESG emissions calculation. |
| `/predict-schedule` | POST | Labor shift scheduling predictions. |
| `/rebalance-optimize` | POST | Multi-facility inventory rebalancing matrix calculation. |
| `/optimize-yield` | POST | Inventory yield optimization and markdown recommendations. |
