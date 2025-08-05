from db.database import SessionLocal
from db.models import Mission
from sqlalchemy.exc import SQLAlchemyError

def get_all_missions():
    session = SessionLocal()
    try:
        return session.query(Mission).order_by(Mission.date.desc()).all()
    except SQLAlchemyError as e:
        print("Database error while fetching missions:", e)
        return []
    finally:
        session.close()

def add_mission(data):
    session = SessionLocal()
    try:
        mission = Mission(**data)
        session.add(mission)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        print("Error adding mission:", e)
        raise
    finally:
        session.close()

def delete_mission(mission_id):
    session = SessionLocal()
    try:
        mission = session.query(Mission).get(mission_id)
        if mission:
            session.delete(mission)
            session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        print("Error deleting mission:", e)
    finally:
        session.close()
