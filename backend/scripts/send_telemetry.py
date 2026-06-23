import requests
import time
import uuid
from datetime import datetime

BASE = 'http://localhost:8000'

trip_id = 'demo_trip'
vehicle_id = 'veh_' + uuid.uuid4().hex[:6]

for i in range(1, 21):
    payload = {
        'vehicle_id': vehicle_id,
        'trip_id': trip_id,
        'lat': 39.9 + i * 0.001,
        'lon': 32.85 + i * 0.001,
        'speed': 80 - i * 0.5,
        'heading': 90,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    try:
        r = requests.post(BASE + '/telemetry', json=payload, timeout=5)
        print(i, r.status_code, r.text)
    except Exception as e:
        print('error', e)
    time.sleep(1)
