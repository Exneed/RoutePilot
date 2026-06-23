# SeferScope - Android Uygulaması

Modern Flutter uygulaması ile Android'e uyumlu, yeşil temayla tasarlanmış otobüs takip sistemi.

## 🎨 Özellikler

- ✅ **Modern Yeşil Tema** - Profesyonel ve şık tasarım
- ✅ **Giriş & Kayıt** - Email, Telefon veya TC Kimlik ile
- ✅ **Sefer Arama** - Rota, Plaka, Firma ile filtrele
- ✅ **Sefer Detayları** - Duraklar ve harita
- ✅ **Koltuk Seçimi** - 50 koltuk grid sistemi
- ✅ **Ödeme** - Özet ve hesaplama
- ✅ **Canlı Takip** - PNR, Hız, ETA, Konum
- ✅ **WebSocket Desteği** - Gerçek zamanlı güncellemeler

## 📱 Kurulum

### Gereksinimler
- Flutter SDK 3.0+
- Android SDK 21+
- Dart 3.0+

### Adımlar

```bash
# 1. Projeye giris
cd bus_tracker_mobile

# 2. Bağımlılıkları yükle
flutter pub get

# 3. Android emulator'u başlat
flutter emulators --launch <emulator-name>

# 4. Uygulamayı çalıştır
flutter run

# 5. Debug modu: Release derlemesi
flutter build apk --release
```

## 🖥️ Backend Bağlantısı

**Emulator Localhost:**
```
http://10.0.2.2:8000
```

Gerçek cihaz için backend IP'sini `lib/services/api_service.dart` dosyasında güncelleyin:
```dart
const String API_BASE_URL = 'http://192.168.x.x:8000';
```

## 📁 Proje Yapısı

```
lib/
├── main.dart                 # Ana giriş noktası
├── models/
│   └── models.dart          # Veri modelleri
├── services/
│   └── api_service.dart     # API bağlantıları
└── screens/
    ├── login_screen.dart    # Giriş/Kayıt
    ├── search_screen.dart   # Sefer arama
    ├── detail_screen.dart   # Sefer detayları
    ├── seats_screen.dart    # Koltuk seçimi
    ├── payment_screen.dart  # Ödeme
    └── tracking_screen.dart # Canlı takip
```

## 🎯 Renk Şeması

- **Ana Yeşil:** #1B7F3D
- **Arka Plan Yeşil:** #0E5323
- **Başarı Yeşili:** #10b981
- **Beyaz:** #FFFFFF
- **Gri:** #F3F4F6

## 🔧 Ekran Gezintisi

```
Login → Search → Detail → Seats → Payment → Tracking → Search
```

## 📱 Ekran Görüntüleri

- **Login Ekranı:** Gradient yeşil arka plan, modern tab UI
- **Sefer Arama:** Filtreleme seçenekleri, sefer kartları
- **Detaylar:** Harita, duraklar, bilgi kartları
- **Koltuk:** 5x10 grid sistemi
- **Ödeme:** Özet tablosu ve PNR
- **Takip:** Gerçek zamanlı veri, istatistikler

## 🚀 Gelecek Özellikler

- [ ] Google Maps entegrasyonu
- [ ] WebSocket canlı takip
- [ ] Bildirim sistemi
- [ ] Ödeme kapısı (Stripe/Iyzico)
- [ ] İstatistikler ve geçmiş
- [ ] Çok dil desteği
- [ ] Tema seçimi (Koyu/Açık)

## 👨‍💻 Geliştirici

SeferScope - Otobüs Takip Sistemi 2026
