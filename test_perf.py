import math
from datetime import datetime, timezone
import time

now = datetime.utcnow()
dates = ["2023-01-01T12:00:00Z"] * 100000

start = time.time()
for date_str in dates:
    clean_date = date_str.replace("Z", "+00:00")
    d_date = datetime.fromisoformat(clean_date)
    if d_date.tzinfo is not None:
        d_date = d_date.astimezone(None).replace(tzinfo=None)
    days_ago = (now - d_date).days
end1 = time.time()

now_utc = datetime.now(timezone.utc)
start2 = time.time()
for date_str in dates:
    clean_date = date_str.replace("Z", "+00:00")
    d_date = datetime.fromisoformat(clean_date)
    if d_date.tzinfo is None:
        d_date = d_date.replace(tzinfo=timezone.utc)
    days_ago = (now_utc - d_date).days
end2 = time.time()

print(f"Original: {end1 - start:.4f}s")
print(f"Optimized: {end2 - start2:.4f}s")
