from backend.app import database
from backend.app.database import Telemetry, SessionLocal
from sqlalchemy import inspect

print('engine url:', database.engine.url)
print('db file exists:', database.engine.url.drivername == 'sqlite')

inspector = inspect(database.engine)
print('tables:', inspector.get_table_names())

session = SessionLocal()
try:
    print('count telemetry:', session.query(Telemetry).count())
    for row in session.query(Telemetry).limit(3):
        print('row', row.id, row.trip_id, row.lat, row.lon, row.created_at)
finally:
    session.close()
