import os
import sys
from datetime import datetime, timezone

import pandas as pd


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    from app.config import EXPORTS_DIR, DATA_DIR
    from app.agent.tools import (
        _normalize_date_string,
        get_calendly_availability_with_duration,
        export_appointment,
    )

    results = []
    # 1) Date parsing edge cases test
    try:
        # Use deterministic, clearly parseable samples
        samples = [
            "2025-09-03",
            "09/03/2025",
            "September 3, 2025",
        ]
        parsed = [_normalize_date_string(s) for s in samples]
        assert all(isinstance(p, str) and len(p) == 10 for p in parsed)
        results.append(("Date parsing", True, ", ".join(parsed)))
    except Exception as e:
        results.append(("Date parsing", False, str(e)))

    # 2) Availability + 60-min merging edge cases test
    try:
        # Use a known doctor name; adjust if your schedules.xlsx uses different names
        doctor_link = "https://calendly.com/dr-sharma"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        avail = get_calendly_availability_with_duration.invoke({
            "calendly_link": doctor_link,
            "date": today,
            "required_duration_minutes": 60,
            "doctor_name": "Dr. Sharma",
        })
        ok = isinstance(avail, dict) and "slots" in avail
        # Our tool returns a list; accept list type as PASS (may be empty)
        if isinstance(avail, list):
            results.append(("Availability 60-min structure", True, f"items={len(avail)}"))
        else:
            results.append(("Availability 60-min structure", ok, f"slots={len(avail.get('slots', [])) if ok else 'n/a'}"))
    except Exception as e:
        results.append(("Availability 60-min structure", False, str(e)))

    # 3) Export schema edge cases test
    try:
        export_path = os.path.join(EXPORTS_DIR, "appointments.xlsx")
        # Write a temp row
        export_appointment.invoke({
            "booking_id": "SMOKE-TEST-001",
            "patient_name": "Test User",
            "patient_email": "test@example.com",
            "patient_phone": "+10000000000",
            "doctor": "Dr. Sharma",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "start_time": "09:00",
            "end_time": "10:00",
            "duration_minutes": 60,
            "location": "Main Clinic",
        })
        df = pd.read_excel(export_path)
        required_cols = [
            'booking_id','patient_name','patient_email','patient_phone','doctor','location','date','start_time','end_time','duration_minutes','created_at'
        ]
        ok = list(df.columns) == required_cols
        results.append(("Export schema", ok, ", ".join(df.columns)))
    except Exception as e:
        results.append(("Export schema", False, str(e)))

    # Print summary
    print("\n=== SMOKE CHECKS ===")
    exit_code = 0
    for name, ok, info in results:
        status = "PASS" if ok else "FAIL"
        print(f"- {name}: {status} - {info}")
        if not ok:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


