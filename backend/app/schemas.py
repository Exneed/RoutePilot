from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TripBase(BaseModel):
    route_name: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float


class TripCreate(TripBase):
    id: str
    vehicle_id: Optional[str] = None


class Trip(TripBase):
    id: str
    vehicle_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TelemetryBase(BaseModel):
    vehicle_id: str
    trip_id: str
    lat: float
    lon: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: datetime


class TelemetryCreate(TelemetryBase):
    pass


class Telemetry(TelemetryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BookingBase(BaseModel):
    pnr: str
    seat_number: Optional[str] = None
    boarding_point: Optional[str] = None
    alighting_point: Optional[str] = None


class BookingCreate(BookingBase):
    user_id: int
    trip_id: str


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    seat_number: Optional[str] = None


class Booking(BookingBase):
    id: int
    user_id: int
    trip_id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
