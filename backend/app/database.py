import os
from pathlib import Path
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, ForeignKey, Boolean, pool, UniqueConstraint, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import OperationalError
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
LOCAL_SQLITE_PATH = BASE_DIR.parent / 'db.sqlite'

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://tracker_user:tracker_pass_123@localhost:5432/bus_tracker'
)

# Use SQLite fallback when PostgreSQL is not reachable
def create_database_engine(url: str):
    if url.startswith('sqlite'):
        return create_engine(url, echo=False, connect_args={"check_same_thread": False})
    return create_engine(url, echo=False, poolclass=pool.NullPool, connect_args={"connect_timeout": 2})

engine = create_database_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        pass
except OperationalError:
    sqlite_url = f"sqlite:///{LOCAL_SQLITE_PATH.as_posix()}"
    print(f"⚠️  PostgreSQL unavailable, switching to SQLite fallback: {sqlite_url}")
    engine = create_database_engine(sqlite_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    tc_id = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    bookings = relationship("Booking", back_populates="user")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    api_key = Column(String, nullable=True)
    api_key_active = Column(Boolean, default=True)
    api_key_created_at = Column(DateTime, nullable=True)
    api_key_rotated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    schedules = relationship("Schedule", back_populates="company")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vehicle_id = Column(String, nullable=False)  # Plaka
    route_name = Column(String, nullable=False)
    departure_time = Column(String, nullable=False)  # HH:MM
    arrival_time = Column(String, nullable=False)  # HH:MM
    price = Column(Float, nullable=False)
    total_seats = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="schedules")
    stops = relationship("Stop", back_populates="schedule", cascade="all, delete-orphan")
    seats = relationship("Seat", back_populates="schedule", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="schedule")


class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    order = Column(Integer, nullable=False)  # Sırası
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    arrival_time = Column(String, nullable=True)  # HH:MM
    departure_time = Column(String, nullable=True)  # HH:MM
    created_at = Column(DateTime, default=datetime.utcnow)

    schedule = relationship("Schedule", back_populates="stops")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    seat_number = Column(String, nullable=False)
    status = Column(String, default="available")  # available, booked, reserved
    created_at = Column(DateTime, default=datetime.utcnow)

    schedule = relationship("Schedule", back_populates="seats")
    __table_args__ = (UniqueConstraint('schedule_id', 'seat_number', name='unique_schedule_seat'),)


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    route_name = Column(String, nullable=False)
    vehicle_id = Column(String, nullable=True)
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lon = Column(Float, nullable=False)
    status = Column(String, default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    telemetries = relationship("Telemetry", back_populates="trip")


class Telemetry(Base):
    __tablename__ = "telemetries"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), index=True)
    vehicle_id = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    trip = relationship("Trip", back_populates="telemetries")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
    pnr = Column(String, unique=True, index=True, nullable=False)
    seat_number = Column(String, nullable=True)
    boarding_point = Column(String, nullable=True)
    alighting_point = Column(String, nullable=True)
    status = Column(String, default="confirmed")  # confirmed, boarded, completed, cancelled
    price = Column(Float, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    schedule = relationship("Schedule", back_populates="bookings")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_company_api_key_columns() -> None:
    try:
        inspector = inspect(engine)
        if not inspector.has_table('companies'):
            return

        existing_columns = {column['name'] for column in inspector.get_columns('companies')}
        statements = []

        if 'api_key' not in existing_columns:
            statements.append("ALTER TABLE companies ADD COLUMN api_key VARCHAR")
        if 'api_key_active' not in existing_columns:
            statements.append("ALTER TABLE companies ADD COLUMN api_key_active BOOLEAN DEFAULT 1")
        if 'api_key_created_at' not in existing_columns:
            statements.append("ALTER TABLE companies ADD COLUMN api_key_created_at DATETIME")
        if 'api_key_rotated_at' not in existing_columns:
            statements.append("ALTER TABLE companies ADD COLUMN api_key_rotated_at DATETIME")

        if not statements:
            return

        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    except Exception as e:
        print(f'⚠️  Failed to upgrade company api key schema: {type(e).__name__}: {e}')


# Create all tables automatically on startup
try:
    Base.metadata.create_all(bind=engine)
    ensure_company_api_key_columns()
except Exception as e:
    print(f'⚠️  Failed to initialize database schema: {type(e).__name__}')
