# RoutePilot- Otobüs Canlı Takip Sistemi

Gerçek zamanlı otobüs konum takibi, canlı harita, WebSocket güncellemeleri ve booking yönetimi sistem.

## Özellikler

✅ **PNR/Plaka ile Sefer Eşleştirme** - Bilet numarası veya plakası ile seferi ara  
✅ **Canlı Telemetri** - Otobüsün konumunu gerçek zamanlı takip et  
✅ **WebSocket Güncellemeleri** - Canlı konum güncellemeleri al  
✅ **Leaflet Harita** - OpenStreetMap tabanlı harita arayüzü  
✅ **Flutter Mobil App** - iOS ve Android için native uygulama  
✅ **REST API** - Detaylı OpenAPI/Swagger spec'i  
✅ **Database Desteği** - PostgreSQL ile trip, booking, telemetry geçmişi  
✅ **Docker** - Containerization ve docker-compose support

## Proje Yapısı

```
SeferScope/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Ana FastAPI uygulaması
│   │   ├── database.py        # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   └── static/
│   │       └── index.html     # Web UI (Leaflet harita)
│   ├── scripts/
│   │   ├── send_telemetry.py  # Demo telemetri gönderici
│   │   └── ws_client.py       # WebSocket test istemcisi
│   ├── requirements.txt        # Python bağımlılıkları
│   └── openapi.yaml           # OpenAPI 3.0 spesifikasyonu
├── flutter_app/               # Flutter mobil uygulama
│   ├── lib/
│   │   ├── main.dart
│   │   ├── services/
│   │   ├── screens/
│   │   └── providers/
│   └── pubspec.yaml
├── Dockerfile                  # Backend containerization
├── docker-compose.yml         # Multi-container orchestration
├── .dockerignore
└── README.md                  # Bu dosya
```

## Hızlı Başlangıç

### 1. Backend Kurulumu

#### Yerel ortamda (Windows)

```powershell
cd <proje-klasoru>

# Virtual environment oluştur
py -3 -m venv .venv

# Etkinleştir
.\.venv\Scripts\Activate.ps1

# Paketleri yükle
pip install -r backend\requirements.txt

# Sunucuyu başlat
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Web arayüzü: http://127.0.0.1:8000  
API Docs: http://127.0.0.1:8000/docs  
OpenAPI JSON: http://127.0.0.1:8000/openapi.json

#### Docker ile

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- PostgreSQL: localhost:5432

### 2. Demo Veri Gönder

Sunucu çalışırken:

```powershell
.\.venv\Scripts\python.exe backend\scripts\send_telemetry.py
```

### 3. Flutter App Kurulumu

```bash
cd flutter_app

flutter pub get

# iOS
flutter run -d ios

# Android
flutter run -d android

# Web (test amaçlı)
flutter run -d chrome
```

## API Endpoints

### Trip Matching

```http
POST /match
Content-Type: application/json

{
  "pnr": "PNR123456",
  "plate": "34 AB 2534"
}
```

**Response:**
```json
{
  "trip_id": "demo_trip",
  "route_name": "Ankara - Kızılay",
  "destination": {"lat": 39.9334, "lon": 32.8597},
  "route": [
    {"lat": 39.900, "lon": 32.850},
    {"lat": 39.9334, "lon": 32.8597}
  ]
}
```

### Telemetry Ingestion

```http
POST /telemetry
Content-Type: application/json

{
  "vehicle_id": "veh_123",
  "trip_id": "demo_trip",
  "lat": 39.915,
  "lon": 32.865,
  "speed": 75.5,
  "heading": 90.0,
  "timestamp": "2026-06-21T23:54:24.109301Z"
}
```

### WebSocket

```
ws://localhost:8000/ws/trip/demo_trip
```

Receives telemetry updates in real-time:
```json
{
  "type": "telemetry",
  "trip_id": "demo_trip",
  "payload": {
    "lat": 39.92,
    "lon": 32.87,
    "speed": 70.0,
    "eta_minutes": 1.5,
    "status": "moving",
    "route": [...]
  }
}
```

### Trip Summary

```http
GET /trip/demo_trip
```

## Database

PostgreSQL şeması:

- **users**: Kullanıcı hesapları
- **trips**: Sefer bilgileri
- **bookings**: Bilet rezervasyonları
- **telemetries**: Konum ve telemetri geçmişi

Başlangıç komutları docker-compose üzerinden otomatik çalıştırılır.

## OpenAPI/Swagger

Backend'in tam API dokümantasyonu:

```bash
# YAML dosyasını görüntüle
cat backend/openapi.yaml

# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

## Geliştirme

### Gerekli Araçlar

- Python 3.13+
- Flutter 3.x
- Docker & Docker Compose
- PostgreSQL 16 (docker-compose ile otomatik)

### Tests

```bash
cd backend

# Unit tests
pytest

# Telemetri testi
python scripts/send_telemetry.py

# WebSocket testi
python scripts/ws_client.py
```

## Deployment

### Docker Push

```bash
docker build -t seferscope-backend .
docker tag seferscope-backend:latest your-registry/seferscope-backend:1.0.0
docker push your-registry/seferscope-backend:1.0.0
```

### Kubernetes (k8s)

```bash
kubectl apply -f k8s/
```

## Yapı Adları

### Backend Sürümleri

- `1.0.0-alpha`: Demo aşaması (telemetry + WS + basic UI)
- `1.0.0-beta`: Database + Flutter entegrasyonu
- `1.0.0`: Üretim sürümü

## Sorun Giderme

### Port zaten kullanımda

```powershell
Get-NetTCPConnection -LocalPort 8000
Stop-Process -Id <PID> -Force
```

### PostgreSQL bağlantısı başarısız

```bash
# Docker container adını kontrol et
docker ps

# Logs
docker logs bus-tracker-db

# Veritabanına bağlan
psql -h localhost -U tracker_user -d bus_tracker
```

### Flutter bağlantı hatası

- Backend URL'ini kontrol et: `http://localhost:8000`
- Android emülatör: `http://10.0.2.2:8000` kullan
- iOS Simulator: `http://localhost:8000`

## Lisans

MIT License - [LICENSE](LICENSE)

## Destek

- GitHub Issues: [GitHub Issues](https://github.com/Exneed/SeferScope/issues)
- Email: support@seferscope.dev

---

**Sürüm:** 1.0.0  
**Son Güncelleme:** 2026-06-22

Flutter push kurulumu notu:

- Gercek cihaz tokeni icin Flutter projeye Firebase baglanmali.
- Gerekli dosyalar:
  - Android: `google-services.json`
  - iOS: `GoogleService-Info.plist`
- Paketler: `firebase_core`, `firebase_messaging`
- Firebase config yoksa uygulama otomatik fallback token ile devam eder.
