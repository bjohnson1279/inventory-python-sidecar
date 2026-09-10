from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
import numpy as np
from sklearn.ensemble import IsolationForest

router = APIRouter()

class LedgerEntryInput(BaseModel):
    sku: str = Field(..., max_length=255)
    location_id: str = Field(..., alias="location_id", max_length=255)
    quantity: int
    reason: str = Field(..., max_length=255)
    actor_id: str = Field(..., alias="actor_id", max_length=255)
    occurred_at: str = Field(..., alias="occurred_at", max_length=255)
    reference_id: Optional[str] = Field(None, alias="reference_id", max_length=255)

    class Config:
        populate_by_name = True

class CycleCountInput(BaseModel):
    sku: str = Field(..., max_length=255)
    location_id: str = Field(..., alias="location_id", max_length=255)
    expected_quantity: int = Field(..., alias="expected_quantity")
    counted_quantity: int = Field(..., alias="counted_quantity")
    counted_at: str = Field(..., alias="counted_at", max_length=255)
    actor_id: str = Field(..., alias="actor_id", max_length=255)

    class Config:
        populate_by_name = True

class ScanEventInput(BaseModel):
    sku: str = Field(..., max_length=255)
    location_id: str = Field(..., alias="location_id", max_length=255)
    scan_context: str = Field(..., alias="scan_context", max_length=1000)
    scanned_at: str = Field(..., alias="scanned_at", max_length=255)
    actor_id: str = Field(..., alias="actor_id", max_length=255)

    class Config:
        populate_by_name = True

class AnomalyDetectRequest(BaseModel):
    ledger_entries: List[LedgerEntryInput] = Field(..., max_length=10000)
    cycle_counts: List[CycleCountInput] = Field(..., max_length=10000)
    scan_events: List[ScanEventInput] = Field(..., max_length=10000)

class AnomalyAlert(BaseModel):
    alert_type: str
    severity: str
    confidence: float
    sku: Optional[str] = None
    location_id: Optional[str] = None
    actor_id: Optional[str] = None
    title: str
    description: str
    evidence: dict
    detected_at: str

    class Config:
        populate_by_name = True

class AnomalyDetectResponse(BaseModel):
    alerts: List[AnomalyAlert]
    summary: dict

    class Config:
        populate_by_name = True


def get_severity(confidence: float) -> str:
    if confidence >= 0.8: return "CRITICAL"
    elif confidence >= 0.6: return "HIGH"
    elif confidence >= 0.4: return "MEDIUM"
    return "LOW"


@router.post("/anomaly-detect", response_model=AnomalyDetectResponse)
def detect_anomalies(req: AnomalyDetectRequest):
    alerts = []
    
    if not req.ledger_entries and not req.cycle_counts and not req.scan_events:
        return AnomalyDetectResponse(
            alerts=[],
            summary={"total_critical": 0, "total_high": 0, "total_medium": 0, "total_low": 0, "overall_risk_score": 0.0}
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    
    # 1. Adjustment Pattern Detector
    actor_loc_stats = {}
    for entry in req.ledger_entries:
        key = (entry.actor_id, entry.location_id)
        if key not in actor_loc_stats:
            actor_loc_stats[key] = {
                "total_negative_qty": 0,
                "shrinkage_count": 0,
                "write_off_count": 0,
                "damage_count": 0,
                "adjustment_frequency": 0,
                "total_qty_mag": 0,
                "entries_count": 0
            }
        
        actor_loc_stats[key]["entries_count"] += 1
        actor_loc_stats[key]["adjustment_frequency"] += 1
        actor_loc_stats[key]["total_qty_mag"] += abs(entry.quantity)
        
        if entry.quantity < 0:
            actor_loc_stats[key]["total_negative_qty"] += abs(entry.quantity)
        
        if entry.reason == "shrinkage":
            actor_loc_stats[key]["shrinkage_count"] += 1
        elif entry.reason == "write_off":
            actor_loc_stats[key]["write_off_count"] += 1
        elif entry.reason == "damage":
            actor_loc_stats[key]["damage_count"] += 1

    if len(actor_loc_stats) >= 5:
        keys = list(actor_loc_stats.keys())
        features = []
        for k in keys:
            stats = actor_loc_stats[k]
            avg_mag = stats["total_qty_mag"] / stats["entries_count"] if stats["entries_count"] > 0 else 0
            features.append([
                stats["total_negative_qty"],
                stats["shrinkage_count"],
                stats["write_off_count"],
                stats["damage_count"],
                stats["adjustment_frequency"],
                avg_mag
            ])
        X = np.array(features)
        
        try:
            iso = IsolationForest(contamination=0.1, random_state=42)
            iso.fit(X)
            scores = iso.decision_function(X)
            
            for i, score in enumerate(scores):
                if score < -0.5:
                    actor_id, location_id = keys[i]
                    conf = min(1.0, max(0.0, abs(score)))
                    alerts.append(AnomalyAlert(
                        alert_type="SHRINKAGE_PATTERN",
                        severity=get_severity(conf),
                        confidence=conf,
                        location_id=location_id,
                        actor_id=actor_id,
                        title="Unusual Shrinkage Pattern Detected",
                        description=f"Isolation Forest flagged anomalous adjustments for actor {actor_id} at {location_id}.",
                        evidence={"isolation_score": float(score), "features": features[i]},
                        detected_at=now_iso
                    ))
        except Exception:
            pass 

    # 2. Cycle Count Discrepancy Analyzer
    loc_counts = {}
    for count in req.cycle_counts:
        loc = count.location_id
        if loc not in loc_counts:
            loc_counts[loc] = []
        var_ratio = (count.counted_quantity - count.expected_quantity) / max(count.expected_quantity, 1)
        loc_counts[loc].append({"ratio": var_ratio, "count": count})

    for loc, data in loc_counts.items():
        if len(data) > 1:
            ratios = [d["ratio"] for d in data]
            mean_ratio = np.mean(ratios)
            std_ratio = np.std(ratios)
            
            if std_ratio > 0:
                for d in data:
                    z_score = (d["ratio"] - mean_ratio) / std_ratio
                    if abs(z_score) > 2:
                        conf = min(1.0, abs(z_score) / 5.0) 
                        alerts.append(AnomalyAlert(
                            alert_type="COUNT_DISCREPANCY",
                            severity=get_severity(conf),
                            confidence=conf,
                            sku=d["count"].sku,
                            location_id=loc,
                            actor_id=d["count"].actor_id,
                            title="Significant Cycle Count Discrepancy",
                            description=f"Z-score {z_score:.2f} for SKU {d['count'].sku} at {loc}.",
                            evidence={"z_score": float(z_score), "variance_ratio": float(d["ratio"])},
                            detected_at=now_iso
                        ))

    # 3. Temporal Anomaly Detector
    try:
        hours = []
        day_counts = {}
        for entry in req.ledger_entries:
            try:
                dt = datetime.fromisoformat(entry.occurred_at.replace("Z", "+00:00"))
                hours.append({"hour": dt.hour, "entry": entry})
                day_str = dt.date().isoformat()
                day_counts[day_str] = day_counts.get(day_str, 0) + 1
            except Exception:
                pass

        if hours:
            hour_vals = [h["hour"] for h in hours]
            q1, q3 = np.percentile(hour_vals, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            for h in hours:
                if h["hour"] < lower_bound or h["hour"] > upper_bound:
                    conf = 0.6
                    alerts.append(AnomalyAlert(
                        alert_type="TIMING_ANOMALY",
                        severity=get_severity(conf),
                        confidence=conf,
                        sku=h["entry"].sku,
                        location_id=h["entry"].location_id,
                        actor_id=h["entry"].actor_id,
                        title="Unusual Adjustment Time",
                        description=f"Adjustment made at hour {h['hour']}, outside normal bounds.",
                        evidence={"hour": h["hour"], "lower_bound": float(lower_bound), "upper_bound": float(upper_bound)},
                        detected_at=now_iso
                    ))

        if day_counts:
            counts = list(day_counts.values())
            if len(counts) > 2:
                mean_counts = np.mean(counts)
                std_counts = np.std(counts)
                for day, count in day_counts.items():
                    if count > mean_counts + 3 * std_counts:
                        conf = 0.8
                        alerts.append(AnomalyAlert(
                            alert_type="TIMING_ANOMALY",
                            severity=get_severity(conf),
                            confidence=conf,
                            title="High Volume Adjustment Burst",
                            description=f"Detected {count} adjustments on {day}, > 3 std devs above mean.",
                            evidence={"date": day, "count": count, "mean": float(mean_counts)},
                            detected_at=now_iso
                        ))
    except Exception:
        pass

    # 4. Actor Risk Scorer
    actor_stats = {}
    for entry in req.ledger_entries:
        a = entry.actor_id
        if a not in actor_stats:
            actor_stats[a] = {"total": 0, "shrinkage": 0, "negative": 0, "temporal_outlier": 0, "cycle_ratios": []}
        actor_stats[a]["total"] += 1
        if entry.reason == "shrinkage":
            actor_stats[a]["shrinkage"] += 1
        if entry.quantity < 0:
            actor_stats[a]["negative"] += 1

    for alert in alerts:
        if alert.alert_type == "TIMING_ANOMALY" and alert.actor_id:
            a = alert.actor_id
            if a in actor_stats:
                actor_stats[a]["temporal_outlier"] += 1

    for count in req.cycle_counts:
        a = count.actor_id
        if a not in actor_stats:
            actor_stats[a] = {"total": 0, "shrinkage": 0, "negative": 0, "temporal_outlier": 0, "cycle_ratios": []}
        var_ratio = abs(count.counted_quantity - count.expected_quantity) / max(count.expected_quantity, 1)
        actor_stats[a]["cycle_ratios"].append(var_ratio)

    for actor, stats in actor_stats.items():
        if stats["total"] > 0:
            shrinkage_ratio = stats["shrinkage"] / stats["total"]
            neg_ratio = stats["negative"] / stats["total"]
        else:
            shrinkage_ratio = 0
            neg_ratio = 0
            
        avg_disc = np.mean(stats["cycle_ratios"]) if stats["cycle_ratios"] else 0
        timing = min(stats["temporal_outlier"] / 5.0, 1.0) 
        
        score = 0.4 * shrinkage_ratio + 0.3 * neg_ratio + 0.2 * min(avg_disc, 1.0) + 0.1 * timing
        if score > 0.6:
            conf = min(1.0, score)
            alerts.append(AnomalyAlert(
                alert_type="ACTOR_RISK",
                severity=get_severity(conf),
                confidence=conf,
                actor_id=actor,
                title="High Risk Actor Identified",
                description=f"Actor {actor} exceeded risk threshold.",
                evidence={"score": float(score), "shrinkage_ratio": float(shrinkage_ratio), "neg_ratio": float(neg_ratio)},
                detected_at=now_iso
            ))

    # Summary
    summary = {"total_critical": 0, "total_high": 0, "total_medium": 0, "total_low": 0, "overall_risk_score": 0.0}
    for a in alerts:
        if a.severity == "CRITICAL": summary["total_critical"] += 1
        elif a.severity == "HIGH": summary["total_high"] += 1
        elif a.severity == "MEDIUM": summary["total_medium"] += 1
        elif a.severity == "LOW": summary["total_low"] += 1

    if alerts:
        summary["overall_risk_score"] = sum([a.confidence for a in alerts]) / len(alerts)

    return AnomalyDetectResponse(alerts=alerts, summary=summary)
