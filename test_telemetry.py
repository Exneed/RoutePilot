#!/usr/bin/env python
"""Send live telemetry data and retrieve it"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("📍 CANLIM TELEMETRI TESTİ")
print("=" * 60)
print()

# Send 5 telemetry points
print("📤 Telemetri gönderiliyor...")
for i in range(5):
    lat = 39.900 + i * 0.005
    lon = 32.850 + i * 0.005
    speed = 40 + i * 5
    
    data = {
        "vehicle_id": "BUS-001",
        "trip_id": "demo_trip",
        "lat": lat,
        "lon": lon,
        "speed": speed,
        "heading": 90.0,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/telemetry", json=data, timeout=5)
        if r.status_code == 200:
            print(f"  ✅ Telemetri {i+1}: Lat={lat:.4f}, Lon={lon:.4f}, Speed={speed} km/h")
        else:
            print(f"  ❌ Telemetri {i+1}: {r.status_code}")
        time.sleep(0.3)
    except Exception as e:
        print(f"  ❌ Hata: {e}")

print()
print("📥 Telemetri Geçmişi Getiriliyor...")
try:
    r = requests.get(f"{BASE_URL}/telemetry/demo_trip?limit=10", timeout=5)
    if r.status_code == 200:
        result = r.json()
        records = result.get('data', [])
        print(f"✅ {len(records)} telemetri kaydı alındı:")
        print()
        for idx, t in enumerate(records[-3:], 1):  # Show last 3
            print(f"  {idx}. Lat={t['lat']:.4f}, Lon={t['lon']:.4f}, Speed={t['speed']} km/h, Time={t['timestamp']}")
    else:
        print(f"❌ Hata: {r.status_code}")
except Exception as e:
    print(f"❌ Hata: {e}")

print()
print("=" * 60)
print("✅ Canlı telemetri testi tamamlandı!")
print("=" * 60)
