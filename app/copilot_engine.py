from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Any

router = APIRouter(prefix="", tags=["copilot"])

class CopilotRequest(BaseModel):
    query: str = Field(..., max_length=1000)

class CopilotResponse(BaseModel):
    query: str
    intent: str
    insights: str
    metricData: Dict[str, Any]
    suggestedActions: List[str]

@router.post("/copilot/query", response_model=CopilotResponse)
def query_copilot(req: CopilotRequest):
    q = req.query.lower()

    if "risk" in q or "stockout" in q:
        intent = "STOCKOUT_RISK_ANALYSIS"
        insights = f"Analysis for query '{req.query}': Current stockout risk is 1.2% across 1,450 active SKUs. SKU-1002 is approaching reorder threshold."
        metrics = {"activeSkus": 1450, "stockoutRiskPercent": 1.2, "atRiskSkus": ["SKU-1002"]}
        actions = ["Trigger purchase order for SKU-1002", "Adjust safety stock level"]
    elif "shrinkage" in q or "theft" in q or "discrepancy" in q:
        intent = "SHRINKAGE_ANOMALY_QUERY"
        insights = f"Analysis for query '{req.query}': Detected 3 stock count discrepancies in Bin B-104 over past 7 days."
        metrics = {"discrepancyCount": 3, "suspiciousBin": "BIN-B-104", "estimatedValueLossCents": 45000}
        actions = ["Schedule physical cycle count for Bin B-104", "Inspect audit log for operator ID 42"]
    else:
        intent = "GENERAL_INVENTORY_QUERY"
        insights = f"Analysis for query '{req.query}': Fulfillment throughput is at 94.5% with optimal inventory turnover."
        metrics = {"totalStockOnHand": 48900, "activeLocations": 12, "openOrders": 154}
        actions = ["Review daily dispatch velocity", "Check supplier OTIF scorecard"]

    return CopilotResponse(
        query=req.query,
        intent=intent,
        insights=insights,
        metricData=metrics,
        suggestedActions=actions
    )
