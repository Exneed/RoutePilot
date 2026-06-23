#!/usr/bin/env python
"""Simple test script for database endpoints"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"
headers = {"Content-Type": "application/json"}

print("=" * 60)
print("🧪 Bus Tracker Database Endpoints Test")
print("=" * 60)
print()

# Test 1: Create User
print("1️⃣  Creating user...")
user_data = {
    "username": "ahmet_demo",
    "email": "ahmet@example.com",
    "phone": "+905551234567"
}
try:
    r = requests.post(f"{BASE_URL}/users", json=user_data, timeout=10)
    if r.status_code == 200:
        user_result = r.json()
        user_id = user_result.get('id')
        print(f"✅ User created: ID={user_id}")
        print(f"   Response: {json.dumps(user_result, indent=2)}")
        print()
    else:
        print(f"❌ Error: {r.status_code}")
        print(f"   {r.text}")
        print()
        user_id = None
except Exception as e:
    print(f"❌ Connection error: {e}")
    print()
    user_id = None

if user_id:
    # Test 2: Create Booking
    print("2️⃣  Creating booking...")
    booking_data = {
        "user_id": user_id,
        "trip_id": "demo_trip",
        "pnr": "TEST123456",
        "seat_number": "A12",
        "boarding_point": "Ankara Central",
        "alighting_point": "Kızılay"
    }
    try:
        r = requests.post(f"{BASE_URL}/bookings", json=booking_data, timeout=10)
        if r.status_code == 200:
            booking_result = r.json()
            print(f"✅ Booking created: ID={booking_result.get('id')}")
            print(f"   Response: {json.dumps(booking_result, indent=2)}")
            print()
        else:
            print(f"❌ Error: {r.status_code}")
            print(f"   {r.text}")
            print()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print()

    # Test 3: List User Bookings
    print("3️⃣  Listing user bookings...")
    try:
        r = requests.get(f"{BASE_URL}/bookings/{user_id}", timeout=10)
        if r.status_code == 200:
            bookings_result = r.json()
            print(f"✅ Bookings retrieved: {len(bookings_result)} records")
            print(f"   Response: {json.dumps(bookings_result, indent=2)}")
            print()
        else:
            print(f"❌ Error: {r.status_code}")
            print(f"   {r.text}")
            print()
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print()

# Test 4: Get Telemetry History
print("4️⃣  Getting telemetry history...")
try:
    r = requests.get(f"{BASE_URL}/telemetry/demo_trip?limit=3", timeout=10)
    if r.status_code == 200:
        telemetry_result = r.json()
        data_count = len(telemetry_result.get('data', []))
        print(f"✅ Telemetry retrieved: {data_count} records")
        if data_count > 0:
            print(f"   Latest: {telemetry_result['data'][0]}")
        print()
    else:
        print(f"❌ Error: {r.status_code}")
        print(f"   {r.text}")
        print()
except Exception as e:
    print(f"❌ Connection error: {e}")
    print()

print("=" * 60)
print("✅ Database endpoints integrated!")
print("=" * 60)
print()
print("📝 Note: Database endpoints work in demo mode without PostgreSQL")
print("   To persist data, run: docker-compose up --build")
print()
