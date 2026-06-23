# SeferScope Backend (MVP skeleton)

Minimal FastAPI backend with WebSocket-based realtime telemetry broadcasting.

Quick start (requires Python 3.10+):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Environment variables:

```bash
# Telemetry ve break endpointleri için API key
TELEMETRY_API_KEY=demo-telemetry-key

# Firma API key yonetimi endpointleri icin admin key
ADMIN_API_KEY=demo-admin-key

# Opsiyonel firma bazli API key haritasi
# Ornek: {"1":{"api_key":"firma-1-key","source":"env"},"2":"firma-2-key"}
COMPANY_API_KEYS_JSON={"1":"firma-1-key"}

# Firebase service account JSON dosya yolu (opsiyonel)
FIREBASE_CREDENTIALS_PATH=C:\path\to\firebase-service-account.json
```

Push notifications:

- `/push/register-token` ile kullanıcı tokenları kaydedilir.
- `/push/test` endpointi Firebase bağlıysa gerçek FCM gönderimi yapar.
- Firebase yapılandırması yoksa endpoint otomatik `fcm_stub` modunda çalışır.
- Web istemcisi önce `/static/firebase-messaging-sw.js` service worker ve `/static/web-push-config.js` konfigürasyonunu kullanarak gerçek FCM token almaya çalışır.
- Firebase web ayarları boş bırakılırsa istemci otomatik pseudo token fallback ile çalışır.

Tenant API key yonetimi:

- `/companies` `GET` endpointi admin icin tum firma listesini ve key ozetini dondurur.
- `/companies/{company_id}/api-key` `GET` endpointi mevcut firma key durumunu dondurur.
- `/companies/{company_id}/api-key` `POST` endpointi yeni key uretir veya verilen key'i kaydeder.
- Bu endpointler `x-admin-key` header'i ile korunur.
- Firma API key degerleri veritabaninda (`companies.api_key`) kalici tutulur; env'den gelen degerler sadece ilk doldurma/fallback icin kullanilir.
- `/telemetry` ve `/trip/{trip_id}/break` endpointleri artik global `TELEMETRY_API_KEY` veya ilgili firmaya ait `x-api-key` ile calisir.

Web FCM scaffold:

- Firebase web ayarlarini `app/static/web-push-config.js` dosyasina girin.
- FCM Web Push icin VAPID key de ayni dosyada `vapidKey` alanina eklenmelidir.
- Service worker dosyasi `app/static/firebase-messaging-sw.js` icinde background bildirimlerini yakalar.
