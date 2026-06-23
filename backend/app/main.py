from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from pathlib import Path
from typing import Dict, List, Any, Optional
import math
from datetime import datetime, timedelta
import uuid
import json
import os
import time
import importlib
import secrets

try:
    firebase_admin = importlib.import_module('firebase_admin')
    credentials = importlib.import_module('firebase_admin.credentials')
    messaging = importlib.import_module('firebase_admin.messaging')
except Exception:
    firebase_admin = None
    credentials = None
    messaging = None

# Database imports
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .database import (
    SessionLocal, Base, engine, User, Company, Schedule, Stop, Seat, Trip, 
    Telemetry as TelemetryModel, Booking, get_db
)

# ===== SCHEMAS =====
class UserRegisterRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    tc_id: Optional[str] = None

class UserLoginRequest(BaseModel):
    email_or_phone_or_tc: str

class ScheduleDetailResponse(BaseModel):
    id: int
    vehicle_id: str
    route_name: str
    departure_time: str
    arrival_time: str
    price: float
    total_seats: int
    company: Optional[Dict] = None
    stops: List[Dict] = []

    class Config:
        from_attributes = True

class BookingNewRequest(BaseModel):
    user_id: int
    schedule_id: int
    seat_number: str
    boarding_point: str
    alighting_point: str

class TelemetryRequest(BaseModel):
    vehicle_id: str
    trip_id: str
    lat: float
    lon: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: str

class BreakEventRequest(BaseModel):
    action: str  # start | end
    company_id: Optional[int] = None
    location_name: Optional[str] = None
    note: Optional[str] = None

class PushTokenRequest(BaseModel):
    user_id: int
    platform: str  # android | ios | web
    token: str

class PushTestRequest(BaseModel):
    user_id: int
    title: str = 'Seferim Nerede'
    body: str = 'Test bildirimi'

class CompanyApiKeyRequest(BaseModel):
    api_key: Optional[str] = None

# ===== FASTAPI APP =====
app = FastAPI(
    title='Bus Tracker MVP Backend',
    version='0.1.0',
    docs_url='/docs',
    redoc_url='/redoc'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

static_dir = Path(__file__).resolve().parent / 'static'
app.mount('/static', StaticFiles(directory=static_dir), name='static')

# ===== GLOBAL STATE =====
TRIPS: Dict[str, Dict[str, Any]] = {}
WS_CONNECTIONS: Dict[str, List[WebSocket]] = {}
USER_PUSH_TOKENS: Dict[int, List[Dict[str, str]]] = {}
RATE_LIMIT_BUCKETS: Dict[str, List[float]] = {}
TELEMETRY_API_KEY = os.getenv('TELEMETRY_API_KEY', 'demo-telemetry-key')
FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', '')
FIREBASE_ENABLED = False
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'demo-admin-key')
COMPANY_API_KEYS_JSON = os.getenv('COMPANY_API_KEYS_JSON', '')
COMPANY_API_KEYS: Dict[int, Dict[str, str]] = {}
TRIP_META: Dict[str, Dict[str, Any]] = {
    'demo_trip': {
        'name': 'Ankara Demo Hattı',
        'name_display': 'Ankara - Kızılay',
        'planned_arrival': '16:30',
        'destination': {'lat': 39.9334, 'lon': 32.8597},
        'route': [
            {'lat': 39.900, 'lon': 32.850},
            {'lat': 39.905, 'lon': 32.855},
            {'lat': 39.910, 'lon': 32.860},
            {'lat': 39.915, 'lon': 32.865},
            {'lat': 39.920, 'lon': 32.867},
            {'lat': 39.925, 'lon': 32.868},
            {'lat': 39.9334, 'lon': 32.8597},
        ],
    }
}

# ===== UTILITIES =====
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def estimate_eta_minutes(last: Dict[str, Any], dest_lat: float, dest_lon: float) -> float:
    speed_kmh = last.get('speed') or 50.0
    distance = haversine_km(last['lat'], last['lon'], dest_lat, dest_lon)
    return distance / max(speed_kmh, 5.0) * 60.0

def estimate_delay_minutes(eta_minutes: Optional[float], planned_arrival_hhmm: Optional[str]) -> Optional[int]:
    if eta_minutes is None or not planned_arrival_hhmm:
        return None

    try:
        now = datetime.now()
        hh, mm = planned_arrival_hhmm.split(':')
        planned_arrival = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        predicted_arrival = now + timedelta(minutes=float(eta_minutes))
        return int(round((predicted_arrival - planned_arrival).total_seconds() / 60.0))
    except Exception:
        return None

def status_from_speed(speed: Optional[float]) -> str:
    if speed is None:
        return 'unknown'
    if speed < 1:
        return 'pause'
    if speed < 25:
        return 'slow'
    return 'moving'

def generate_pnr() -> str:
    return f"BOOK-{datetime.now().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:5].upper()}"

def verify_api_key(x_api_key: Optional[str]) -> None:
    if not x_api_key or x_api_key != TELEMETRY_API_KEY:
        raise HTTPException(status_code=401, detail='Geçersiz API anahtarı')

def verify_admin_api_key(x_admin_key: Optional[str]) -> None:
    if not x_admin_key or x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail='Geçersiz admin anahtarı')

def enforce_rate_limit(client_key: str, limit: int = 120, window_sec: int = 60) -> None:
    now = time.time()
    bucket = RATE_LIMIT_BUCKETS.setdefault(client_key, [])
    bucket[:] = [ts for ts in bucket if now - ts <= window_sec]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail='Rate limit aşıldı')
    bucket.append(now)

def init_firebase() -> bool:
    global FIREBASE_ENABLED

    if firebase_admin is None or credentials is None:
        FIREBASE_ENABLED = False
        return False

    try:
        if not firebase_admin._apps:
            if not FIREBASE_CREDENTIALS_PATH:
                FIREBASE_ENABLED = False
                return False
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
        return True
    except Exception:
        FIREBASE_ENABLED = False
        return False

def send_push_to_tokens(tokens: List[str], title: str, body: str) -> Dict[str, Any]:
    if not tokens:
        return {
            'provider': 'none',
            'success_count': 0,
            'failure_count': 0,
            'note': 'Hedef token bulunamadı'
        }

    if not FIREBASE_ENABLED or messaging is None:
        return {
            'provider': 'fcm_stub',
            'success_count': len(tokens),
            'failure_count': 0,
            'note': 'Firebase yapılandırması yok, dry-run çalıştı'
        }

    try:
        multicast = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
            data={'source': 'seferim-nerede-backend'}
        )
        response = messaging.send_each_for_multicast(multicast)
        return {
            'provider': 'fcm',
            'success_count': response.success_count,
            'failure_count': response.failure_count,
            'note': 'Firebase üzerinden gönderildi'
        }
    except Exception as e:
        return {
            'provider': 'fcm_error',
            'success_count': 0,
            'failure_count': len(tokens),
            'note': str(e)
        }

def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return '*' * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"

def load_company_api_keys() -> None:
    global COMPANY_API_KEYS
    if not COMPANY_API_KEYS_JSON:
        return
    try:
        raw = json.loads(COMPANY_API_KEYS_JSON)
        if not isinstance(raw, dict):
            return
        normalized: Dict[int, Dict[str, str]] = {}
        for key, value in raw.items():
            try:
                company_id = int(key)
            except Exception:
                continue
            if isinstance(value, str):
                normalized[company_id] = {'api_key': value, 'source': 'env'}
            elif isinstance(value, dict) and value.get('api_key'):
                normalized[company_id] = {'api_key': str(value['api_key']), 'source': str(value.get('source', 'env'))}
        COMPANY_API_KEYS.update(normalized)
    except Exception:
        pass

def sync_company_api_keys_to_db() -> None:
    if not COMPANY_API_KEYS:
        return

    db = SessionLocal()
    try:
        changed = False
        for company_id, meta in COMPANY_API_KEYS.items():
            company = db.query(Company).filter(Company.id == company_id).first()
            if not company or company.api_key:
                continue

            company.api_key = meta.get('api_key')
            company.api_key_active = True
            company.api_key_created_at = datetime.utcnow()
            company.api_key_rotated_at = datetime.utcnow()
            changed = True

        if changed:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def resolve_company(db: Session, company_id: Optional[int] = None, vehicle_id: Optional[str] = None) -> Optional[Company]:
    if company_id is not None:
        return db.query(Company).filter(Company.id == company_id).first()
    if vehicle_id:
        schedule = db.query(Schedule).filter(Schedule.vehicle_id == vehicle_id).first()
        if schedule:
            return db.query(Company).filter(Company.id == schedule.company_id).first()
    return None

def get_company_api_key_meta(company: Optional[Company]) -> Optional[Dict[str, str]]:
    if company and company.api_key and company.api_key_active:
        return {'api_key': company.api_key, 'source': 'database'}
    if company:
        return COMPANY_API_KEYS.get(company.id)
    return None

def upsert_company_api_key(db: Session, company: Company, api_key: str, source: str = 'dashboard') -> Dict[str, str]:
    now = datetime.utcnow()
    company.api_key = api_key
    company.api_key_active = True
    company.api_key_created_at = company.api_key_created_at or now
    company.api_key_rotated_at = now
    db.add(company)
    db.commit()
    db.refresh(company)

    meta = {'api_key': api_key, 'source': source}
    COMPANY_API_KEYS[company.id] = meta
    return meta

def serialize_company_admin(company: Company) -> Dict[str, Any]:
    meta = get_company_api_key_meta(company)
    return {
        'company_id': company.id,
        'company_name': company.name,
        'phone': company.phone,
        'email': company.email,
        'has_api_key': bool(meta),
        'masked_api_key': mask_api_key(meta.get('api_key') if meta else None),
        'source': meta.get('source') if meta else None,
        'api_key_active': bool(company.api_key_active) if company.api_key_active is not None else bool(meta),
        'api_key_rotated_at': company.api_key_rotated_at.isoformat() if company.api_key_rotated_at else None,
    }

def resolve_company_id_by_vehicle(db: Session, vehicle_id: Optional[str]) -> Optional[int]:
    if not vehicle_id:
        return None
    schedule = db.query(Schedule).filter(Schedule.vehicle_id == vehicle_id).first()
    return schedule.company_id if schedule else None

def verify_transport_api_key(
    x_api_key: Optional[str],
    db: Optional[Session] = None,
    vehicle_id: Optional[str] = None,
    company_id: Optional[int] = None,
) -> Dict[str, Any]:
    if x_api_key and x_api_key == TELEMETRY_API_KEY:
        return {'scope': 'global'}

    resolved_company_id = company_id
    company = None
    if db is not None:
        company = resolve_company(db, company_id=company_id, vehicle_id=vehicle_id)
        resolved_company_id = company.id if company else resolved_company_id

    company_meta = get_company_api_key_meta(company) if company else (COMPANY_API_KEYS.get(resolved_company_id) if resolved_company_id is not None else None)
    if company_meta and x_api_key == company_meta.get('api_key'):
        return {'scope': 'company', 'company_id': resolved_company_id}

    raise HTTPException(status_code=401, detail='Geçersiz taşıyıcı API anahtarı')

init_firebase()
load_company_api_keys()
sync_company_api_keys_to_db()

# ===== HOME PAGE =====
@app.get('/', response_class=HTMLResponse)
async def home():
    """Ana sayfa"""
    return FileResponse(static_dir / 'index.html')

# ===== HEALTH CHECK =====
@app.get('/health')
async def health_check():
    """Sistem sağlık kontrolü"""
    return {'status': 'ok', 'message': 'Bus Tracker backend is running'}

# ===== AUTH ENDPOINTS =====
@app.post('/auth/register')
async def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Kullanıcı kaydı - Email, Telefon veya TC Kimlik ile"""
    try:
        # Check if user already exists
        if req.email:
            existing = db.query(User).filter(User.email == req.email).first()
            if existing:
                raise HTTPException(status_code=400, detail='Email zaten kayıtlı')
        
        if req.phone:
            existing = db.query(User).filter(User.phone == req.phone).first()
            if existing:
                raise HTTPException(status_code=400, detail='Telefon zaten kayıtlı')
        
        if req.tc_id:
            existing = db.query(User).filter(User.tc_id == req.tc_id).first()
            if existing:
                raise HTTPException(status_code=400, detail='TC Kimlik zaten kayıtlı')
        
        # Create new user - ensure None values instead of empty strings
        user = User(
            email=req.email or None,
            phone=req.phone or None,
            tc_id=req.tc_id or None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return {
            'user_id': user.id,
            'email': user.email,
            'phone': user.phone,
            'tc_id': user.tc_id,
            'token': f'demo_token_{user.id}'
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=503, content={'error': str(e)})

@app.post('/auth/login')
async def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Kullanıcı girişi - Email, Telefon veya TC Kimlik ile"""
    try:
        # Search by email, phone or tc_id
        user = db.query(User).filter(
            (User.email == req.email_or_phone_or_tc) |
            (User.phone == req.email_or_phone_or_tc) |
            (User.tc_id == req.email_or_phone_or_tc)
        ).first()
        
        if not user:
            raise HTTPException(status_code=404, detail='Kullanıcı bulunamadı')
        
        return {
            'user_id': user.id,
            'email': user.email,
            'phone': user.phone,
            'tc_id': user.tc_id,
            'token': f'demo_token_{user.id}'
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=503, content={'error': str(e)})

# ===== INIT DEMO DATA =====
@app.post('/init')
async def init_demo_data(db: Session = Depends(get_db)):
    """Demo verisi başlat"""
    try:
        # Check if company exists
        company = db.query(Company).filter(Company.name == 'Özkaymak Turizm').first()
        if not company:
            company = Company(
                name='Özkaymak Turizm',
                phone='+905551234567',
                email='info@ozkaymak.com',
                logo_url='https://placeholder.com/logo.png'
            )
            db.add(company)
            db.commit()
            db.refresh(company)
        
        # Demo schedules
        demo_schedules = [
            {
                'vehicle_id': '06 ABC 0001',
                'route_name': 'Ankara - Pamukkale',
                'departure_time': '08:00',
                'arrival_time': '16:30',
                'price': 250,
                'stops': [
                    {'order': 1, 'name': 'Ankara Merkez', 'lat': 39.9334, 'lon': 32.8597, 'arrival_time': '08:00', 'departure_time': '08:00'},
                    {'order': 2, 'name': 'Konya', 'lat': 38.7325, 'lon': 33.5031, 'arrival_time': '11:30', 'departure_time': '11:45'},
                    {'order': 3, 'name': 'Pamukkale', 'lat': 37.9202, 'lon': 29.1232, 'arrival_time': '16:30', 'departure_time': '16:30'},
                ]
            },
            {
                'vehicle_id': '06 ABC 0002',
                'route_name': 'İstanbul - Ankara',
                'departure_time': '09:00',
                'arrival_time': '14:30',
                'price': 200,
                'stops': [
                    {'order': 1, 'name': 'İstanbul Otogarı', 'lat': 41.2868, 'lon': 28.9846, 'arrival_time': '09:00', 'departure_time': '09:00'},
                    {'order': 2, 'name': 'Ankara Merkez', 'lat': 39.9334, 'lon': 32.8597, 'arrival_time': '14:30', 'departure_time': '14:30'},
                ]
            },
            {
                'vehicle_id': '06 ABC 0003',
                'route_name': 'Ankara - İzmir',
                'departure_time': '10:00',
                'arrival_time': '18:00',
                'price': 280,
                'stops': [
                    {'order': 1, 'name': 'Ankara Merkez', 'lat': 39.9334, 'lon': 32.8597, 'arrival_time': '10:00', 'departure_time': '10:00'},
                    {'order': 2, 'name': 'Afyonkarahisar', 'lat': 38.7507, 'lon': 30.5566, 'arrival_time': '12:30', 'departure_time': '12:45'},
                    {'order': 3, 'name': 'İzmir', 'lat': 38.4161, 'lon': 27.1398, 'arrival_time': '18:00', 'departure_time': '18:00'},
                ]
            }
        ]
        
        for sched_data in demo_schedules:
            # Check if schedule exists
            existing = db.query(Schedule).filter(
                and_(Schedule.company_id == company.id, Schedule.vehicle_id == sched_data['vehicle_id'])
            ).first()
            if existing:
                continue
            
            schedule = Schedule(
                company_id=company.id,
                vehicle_id=sched_data['vehicle_id'],
                route_name=sched_data['route_name'],
                departure_time=sched_data['departure_time'],
                arrival_time=sched_data['arrival_time'],
                price=sched_data['price'],
                total_seats=50
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            # Add stops
            for stop_data in sched_data['stops']:
                existing_stop = db.query(Stop).filter(
                    and_(Stop.schedule_id == schedule.id, Stop.order == stop_data['order'])
                ).first()
                if not existing_stop:
                    stop = Stop(
                        schedule_id=schedule.id,
                        order=stop_data['order'],
                        name=stop_data['name'],
                        lat=stop_data['lat'],
                        lon=stop_data['lon'],
                        arrival_time=stop_data['arrival_time'],
                        departure_time=stop_data['departure_time']
                    )
                    db.add(stop)
            
            db.commit()
            
            # Add 50 seats
            for seat_num in range(1, 51):
                existing_seat = db.query(Seat).filter(
                    and_(Seat.schedule_id == schedule.id, Seat.seat_number == str(seat_num))
                ).first()
                if not existing_seat:
                    seat = Seat(
                        schedule_id=schedule.id,
                        seat_number=str(seat_num),
                        status='available'
                    )
                    db.add(seat)
            
            db.commit()
        
        return {'status': 'ok', 'message': 'Demo verisi yüklendi'}
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=503, content={'error': str(e)})

# ===== SCHEDULE ENDPOINTS =====
@app.get('/schedules/search')
async def search_schedules(
    route: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    company: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Sefer arama - Rota, Plaka, Firma ile filtrele"""
    try:
        query = db.query(Schedule).join(Company).filter()
        
        if route:
            query = query.filter(Schedule.route_name.ilike(f'%{route}%'))
        if vehicle_id:
            query = query.filter(Schedule.vehicle_id.ilike(f'%{vehicle_id}%'))
        if company:
            query = query.filter(Company.name.ilike(f'%{company}%'))
        
        schedules = query.all()
        
        result = []
        for schedule in schedules:
            result.append({
                'id': schedule.id,
                'vehicle_id': schedule.vehicle_id,
                'route_name': schedule.route_name,
                'departure_time': schedule.departure_time,
                'arrival_time': schedule.arrival_time,
                'price': schedule.price,
                'total_seats': schedule.total_seats,
                'company': {
                    'id': schedule.company.id,
                    'name': schedule.company.name,
                    'phone': schedule.company.phone,
                    'email': schedule.company.email,
                    'logo_url': schedule.company.logo_url
                }
            })
        
        return result
    except Exception as e:
        return JSONResponse(status_code=503, content={'error': str(e)})

@app.get('/schedules/{schedule_id}')
async def get_schedule_detail(schedule_id: int, db: Session = Depends(get_db)):
    """Sefer detayları ve durakları"""
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail='Sefer bulunamadı')
        
        stops = db.query(Stop).filter(Stop.schedule_id == schedule_id).order_by(Stop.order).all()
        
        return {
            'id': schedule.id,
            'vehicle_id': schedule.vehicle_id,
            'route_name': schedule.route_name,
            'departure_time': schedule.departure_time,
            'arrival_time': schedule.arrival_time,
            'price': schedule.price,
            'total_seats': schedule.total_seats,
            'company': {
                'id': schedule.company.id,
                'name': schedule.company.name,
                'phone': schedule.company.phone,
                'email': schedule.company.email,
                'logo_url': schedule.company.logo_url
            },
            'stops': [
                {
                    'id': s.id,
                    'order': s.order,
                    'name': s.name,
                    'lat': s.lat,
                    'lon': s.lon,
                    'arrival_time': s.arrival_time,
                    'departure_time': s.departure_time
                }
                for s in stops
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=503, content={'error': str(e)})

@app.get('/schedules/{schedule_id}/seats')
async def get_available_seats(schedule_id: int, db: Session = Depends(get_db)):
    """Boş ve dolu koltukları listele"""
    try:
        seats = db.query(Seat).filter(Seat.schedule_id == schedule_id).all()
        
        available = [s.seat_number for s in seats if s.status == 'available']
        booked = [s.seat_number for s in seats if s.status in ('booked', 'reserved')]
        
        return {
            'schedule_id': schedule_id,
            'available': available,
            'booked': booked,
            'available_count': len(available),
            'booked_count': len(booked)
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={'error': str(e)})

# ===== BOOKING ENDPOINTS =====
@app.post('/bookings/new')
async def create_booking(req: BookingNewRequest, db: Session = Depends(get_db)):
    """Yeni rezervasyon oluştur"""
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='Kullanıcı bulunamadı')
        
        # Verify schedule exists
        schedule = db.query(Schedule).filter(Schedule.id == req.schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=404, detail='Sefer bulunamadı')
        
        # Check seat availability
        seat = db.query(Seat).filter(
            and_(Seat.schedule_id == req.schedule_id, Seat.seat_number == req.seat_number)
        ).first()
        if not seat:
            raise HTTPException(status_code=404, detail='Koltuk bulunamadı')
        if seat.status != 'available':
            raise HTTPException(status_code=400, detail='Koltuk dolu')
        
        # Mark seat as booked
        seat.status = 'booked'
        
        # Create booking
        pnr = generate_pnr()
        booking = Booking(
            user_id=req.user_id,
            schedule_id=req.schedule_id,
            trip_id='demo_trip',
            pnr=pnr,
            seat_number=req.seat_number,
            boarding_point=req.boarding_point,
            alighting_point=req.alighting_point,
            status='confirmed',
            price=schedule.price
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        return {
            'id': booking.id,
            'pnr': booking.pnr,
            'schedule_id': booking.schedule_id,
            'seat_number': booking.seat_number,
            'status': booking.status,
            'price': booking.price,
            'created_at': booking.created_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return JSONResponse(status_code=503, content={'error': str(e)})

# ===== TELEMETRY ENDPOINTS =====
@app.post('/telemetry')
async def ingest_telemetry(
    t: TelemetryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None)
):
    try:
        verify_transport_api_key(x_api_key, db=db, vehicle_id=t.vehicle_id)
        enforce_rate_limit(f'telemetry:{t.vehicle_id}')

        trip_state = TRIPS.setdefault(t.trip_id, {})
        trip_state['last'] = {
            'lat': t.lat,
            'lon': t.lon,
            'speed': t.speed,
            'heading': t.heading,
            'timestamp': t.timestamp
        }
        trip_state['status'] = status_from_speed(t.speed)

        # Save to database
        try:
            db_telemetry = TelemetryModel(
                trip_id=t.trip_id,
                vehicle_id=t.vehicle_id,
                lat=t.lat,
                lon=t.lon,
                speed=t.speed,
                heading=t.heading,
                timestamp=datetime.fromisoformat(t.timestamp.replace('Z', '+00:00')) if isinstance(t.timestamp, str) else t.timestamp
            )
            db.add(db_telemetry)
            db.commit()
        except:
            db.rollback()
        
        # Broadcast via WebSocket
        async def broadcast():
            trip_meta = TRIP_META.get(t.trip_id, {})
            route = trip_meta.get('route', [])
            dest = trip_meta.get('destination', {'lat': 39.9334, 'lon': 32.8597})
            eta = None
            try:
                eta = estimate_eta_minutes(trip_state['last'], dest['lat'], dest['lon'])
            except:
                eta = None
            delay_minutes = estimate_delay_minutes(eta, trip_meta.get('planned_arrival'))
            
            payload = {
                'lat': t.lat,
                'lon': t.lon,
                'speed': t.speed,
                'heading': t.heading,
                'eta': eta,
                'delay_minutes': delay_minutes,
                'is_delayed': (delay_minutes or 0) > 0,
                'status': trip_state['status'],
                'route': route,
            }
            
            conns = WS_CONNECTIONS.get(t.trip_id, [])
            to_remove = []
            for ws in conns:
                try:
                    await ws.send_json(payload)
                except:
                    to_remove.append(ws)
            for ws in to_remove:
                if ws in conns:
                    conns.remove(ws)
        
        background_tasks.add_task(broadcast)
        return {'status': 'ok'}
    except Exception as e:
        return JSONResponse(status_code=503, content={'error': str(e)})

# ===== WEBSOCKET ENDPOINT =====
@app.websocket('/ws/trip/{trip_id}')
async def websocket_endpoint(websocket: WebSocket, trip_id: str):
    """WebSocket - Canlı sefer takibi"""
    await websocket.accept()
    WS_CONNECTIONS.setdefault(trip_id, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        conns = WS_CONNECTIONS.get(trip_id, [])
        if websocket in conns:
            conns.remove(websocket)

@app.post('/trip/{trip_id}/break')
async def update_break_status(
    trip_id: str,
    req: BreakEventRequest,
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None)
):
    """Mola başladı/bitti eventi üretir ve WebSocket'e yayınlar."""
    verify_transport_api_key(x_api_key, db=db, company_id=req.company_id)
    enforce_rate_limit(f'break:{trip_id}', limit=30, window_sec=60)

    action = (req.action or '').strip().lower()
    if action not in {'start', 'end'}:
        return JSONResponse({'error': 'action start veya end olmalı'}, status_code=400)

    trip_state = TRIPS.setdefault(trip_id, {})
    now_iso = datetime.now().isoformat()

    if action == 'start':
        trip_state['break_active'] = True
        trip_state['break_since'] = now_iso
        event_type = 'break_started'
    else:
        trip_state['break_active'] = False
        trip_state['break_ended_at'] = now_iso
        event_type = 'break_ended'

    payload = {
        'event': event_type,
        'trip_id': trip_id,
        'timestamp': now_iso,
        'location_name': req.location_name,
        'note': req.note,
        'break_active': trip_state.get('break_active', False),
    }

    conns = WS_CONNECTIONS.get(trip_id, [])
    to_remove = []
    for ws in conns:
        try:
            await ws.send_json(payload)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        if ws in conns:
            conns.remove(ws)

    all_tokens: List[str] = []
    for user_tokens in USER_PUSH_TOKENS.values():
        all_tokens.extend([item.get('token', '') for item in user_tokens if item.get('token')])
    if all_tokens:
        push_title = 'Sefer Durumu Güncellendi'
        push_body = 'Mola başladı' if event_type == 'break_started' else 'Mola bitti, sefer devam ediyor'
        send_push_to_tokens(all_tokens, push_title, push_body)

    return payload

@app.post('/push/register-token')
async def register_push_token(req: PushTokenRequest):
    """Kullanıcı push token kaydı (FCM/APNS entegrasyonu için hazırlık)."""
    platform = (req.platform or '').strip().lower()
    if platform not in {'android', 'ios', 'web'}:
        return JSONResponse({'error': 'platform android/ios/web olmalı'}, status_code=400)

    tokens = USER_PUSH_TOKENS.setdefault(req.user_id, [])
    exists = any(item.get('token') == req.token for item in tokens)
    if not exists:
        tokens.append({'platform': platform, 'token': req.token})

    return {
        'status': 'registered',
        'user_id': req.user_id,
        'token_count': len(tokens)
    }

@app.post('/push/test')
async def send_test_push(req: PushTestRequest):
    """FCM test bildirimi (firebase_admin varsa gerçek, yoksa stub)."""
    token_items = USER_PUSH_TOKENS.get(req.user_id, [])
    tokens = [item.get('token', '') for item in token_items if item.get('token')]
    push_result = send_push_to_tokens(tokens, req.title, req.body)

    return {
        'status': 'queued',
        'provider': push_result.get('provider'),
        'user_id': req.user_id,
        'title': req.title,
        'body': req.body,
        'target_count': len(tokens),
        'success_count': push_result.get('success_count', 0),
        'failure_count': push_result.get('failure_count', 0),
        'tokens': token_items,
        'note': push_result.get('note')
    }

@app.get('/companies')
async def list_companies(
    db: Session = Depends(get_db),
    x_admin_key: Optional[str] = Header(default=None),
):
    verify_admin_api_key(x_admin_key)
    companies = db.query(Company).order_by(Company.name.asc()).all()
    return {'items': [serialize_company_admin(company) for company in companies]}

@app.get('/companies/{company_id}/api-key')
async def get_company_api_key(
    company_id: int,
    db: Session = Depends(get_db),
    x_admin_key: Optional[str] = Header(default=None),
):
    verify_admin_api_key(x_admin_key)
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail='Firma bulunamadı')

    meta = get_company_api_key_meta(company)
    return {
        **serialize_company_admin(company),
        'global_fallback_enabled': bool(TELEMETRY_API_KEY),
    }

@app.post('/companies/{company_id}/api-key')
async def create_or_rotate_company_api_key(
    company_id: int,
    payload: CompanyApiKeyRequest,
    db: Session = Depends(get_db),
    x_admin_key: Optional[str] = Header(default=None),
):
    verify_admin_api_key(x_admin_key)
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail='Firma bulunamadı')

    api_key = payload.api_key.strip() if payload.api_key else secrets.token_urlsafe(24)
    meta = upsert_company_api_key(db, company, api_key, source='dashboard')
    return {
        'company_id': company.id,
        'company_name': company.name,
        'api_key': meta['api_key'],
        'masked_api_key': mask_api_key(meta['api_key']),
        'source': meta['source'],
        'api_key_rotated_at': company.api_key_rotated_at.isoformat() if company.api_key_rotated_at else None,
        'message': 'Firma API anahtarı kaydedildi',
    }

# ===== LEGACY ENDPOINTS =====
@app.get('/trip/{trip_id}')
async def get_trip_summary(trip_id: str):
    """Sefer özeti - Legacy"""
    trip = TRIPS.get(trip_id)
    if not trip:
        return JSONResponse({'error': 'trip not found'}, status_code=404)
    
    last = trip.get('last')
    eta = None
    delay_minutes = None
    if last:
        trip_meta = TRIP_META.get(trip_id, {})
        dest = trip_meta.get('destination', {'lat': 39.9334, 'lon': 32.8597})
        eta = estimate_eta_minutes(last, dest['lat'], dest['lon'])
        delay_minutes = estimate_delay_minutes(eta, trip_meta.get('planned_arrival'))
    
    return {
        'trip_id': trip_id,
        'route_name': TRIP_META.get(trip_id, {}).get('name_display'),
        'last': last,
        'status': trip.get('status', 'unknown'),
        'eta_minutes': eta,
        'delay_minutes': delay_minutes,
        'is_delayed': (delay_minutes or 0) > 0,
        'break_active': trip.get('break_active', False),
        'break_since': trip.get('break_since'),
        'route': TRIP_META.get(trip_id, {}).get('route', []),
        'destination': TRIP_META.get(trip_id, {}).get('destination'),
    }

@app.post('/match')
async def match_trip(pnr: Optional[str] = None, plate: Optional[str] = None):
    """Sefer eşleştir - Legacy"""
    if not pnr and not plate:
        return JSONResponse({'error': 'pnr veya plate giriniz'}, status_code=400)
    
    trip_id = 'demo_trip'
    route = TRIP_META[trip_id]['route']
    destination = TRIP_META[trip_id]['destination']
    
    return {
        'trip_id': trip_id,
        'route_name': TRIP_META[trip_id]['name_display'],
        'destination': destination,
        'route': route,
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
