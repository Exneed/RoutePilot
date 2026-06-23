# Test Bus Tracker Database Endpoints
# PowerShell script to test new database endpoints

$BASE_URL = "http://127.0.0.1:8000"
$headers = @{"Content-Type" = "application/json"}

Write-Host "=== Bus Tracker Backend API Test ===" -ForegroundColor Green
Write-Host ""

# Test 1: Create User
Write-Host "1️⃣  Creating user..." -ForegroundColor Cyan
$user_data = @{
    username = "ahmet_test"
    email = "ahmet@example.com"
    phone = "+905551234567"
} | ConvertTo-Json

try {
    $user_response = Invoke-WebRequest -Uri "$BASE_URL/users" `
        -Method POST `
        -Headers $headers `
        -Body $user_data `
        -ErrorAction Stop
    
    $user_id = ($user_response.Content | ConvertFrom-Json).id
    Write-Host "✅ User created: ID=$user_id" -ForegroundColor Green
    Write-Host $user_response.Content | ConvertFrom-Json | ConvertTo-Json
    Write-Host ""
} catch {
    Write-Host "❌ Error creating user:" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode
    Write-Host ""
}

# Test 2: Create Booking
Write-Host "2️⃣  Creating booking..." -ForegroundColor Cyan
$booking_data = @{
    user_id = $user_id
    trip_id = "demo_trip"
    pnr = "TEST123456"
    seat_number = "A12"
    boarding_point = "Ankara Central"
    alighting_point = "Kızılay"
} | ConvertTo-Json

try {
    $booking_response = Invoke-WebRequest -Uri "$BASE_URL/bookings" `
        -Method POST `
        -Headers $headers `
        -Body $booking_data `
        -ErrorAction Stop
    
    $booking_id = ($booking_response.Content | ConvertFrom-Json).id
    Write-Host "✅ Booking created: ID=$booking_id" -ForegroundColor Green
    Write-Host $booking_response.Content | ConvertFrom-Json | ConvertTo-Json
    Write-Host ""
} catch {
    Write-Host "❌ Error creating booking:" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode
    Write-Host $_.Exception.Response.Content
    Write-Host ""
}

# Test 3: List User Bookings
Write-Host "3️⃣  Listing user bookings..." -ForegroundColor Cyan
try {
    $bookings_response = Invoke-WebRequest -Uri "$BASE_URL/bookings/$user_id" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    Write-Host "✅ Bookings retrieved:" -ForegroundColor Green
    Write-Host $bookings_response.Content | ConvertFrom-Json | ConvertTo-Json
    Write-Host ""
} catch {
    Write-Host "❌ Error listing bookings:" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode
    Write-Host ""
}

# Test 4: Get Telemetry History
Write-Host "4️⃣  Getting telemetry history..." -ForegroundColor Cyan
try {
    $telemetry_response = Invoke-WebRequest -Uri "$BASE_URL/telemetry/demo_trip?limit=5" `
        -Method GET `
        -Headers $headers `
        -ErrorAction Stop
    
    Write-Host "✅ Telemetry retrieved:" -ForegroundColor Green
    $telemetry_data = $telemetry_response.Content | ConvertFrom-Json
    Write-Host "Trip ID: $($telemetry_data.trip_id)" -ForegroundColor Yellow
    Write-Host "Records: $($telemetry_data.data.Length)" -ForegroundColor Yellow
    Write-Host ""
} catch {
    Write-Host "❌ Error getting telemetry:" -ForegroundColor Red
    Write-Host $_.Exception.Response.StatusCode
    Write-Host ""
}

# Test 5: Match Trip (Demo)
Write-Host "5️⃣  Demo: Matching trip..." -ForegroundColor Cyan
$match_data = @{
    pnr = "TEST123456"
    plate = "34ABC1234"
} | ConvertTo-Json

try {
    $match_response = Invoke-WebRequest -Uri "$BASE_URL/match" `
        -Method POST `
        -Headers $headers `
        -Body $match_data `
        -ErrorAction Stop
    
    Write-Host "✅ Trip matched:" -ForegroundColor Green
    Write-Host $match_response.Content | ConvertFrom-Json | ConvertTo-Json
    Write-Host ""
} catch {
    Write-Host "❌ Error matching trip:" -ForegroundColor Red
    Write-Host ""
}

Write-Host "=== Test Complete ===" -ForegroundColor Green
