import cProfile
from app.anomaly_detector import detect_anomalies, AnomalyDetectRequest, LedgerEntryInput, CycleCountInput, ScanEventInput
import random
from datetime import datetime, timedelta, timezone

def generate_anomaly_data():
    now = datetime.now(timezone.utc)
    entries = []
    for i in range(10000):
        qty = random.randint(-10, 10)
        dt = (now - timedelta(hours=random.randint(0, 100))).isoformat()
        reason = random.choice(["shrinkage", "write_off", "damage", "normal"])
        entries.append(LedgerEntryInput(
            id=f"LE{i}", sku=f"SKU{i%100}", location_id=f"L{i%10}",
            quantity=qty, occurred_at=dt, reason=reason, actor_id=f"A{i%50}"
        ))
    counts = []
    for i in range(2000):
        counts.append(CycleCountInput(
            id=f"CC{i}", sku=f"SKU{i%100}", location_id=f"L{i%10}",
            expected_quantity=100, counted_quantity=random.randint(90, 110),
            actor_id=f"A{i%50}", counted_at=now.isoformat()
        ))
    scans = []
    return AnomalyDetectRequest(ledger_entries=entries, cycle_counts=counts, scan_events=scans)

req = generate_anomaly_data()
cProfile.run('detect_anomalies(req)', sort='tottime')
