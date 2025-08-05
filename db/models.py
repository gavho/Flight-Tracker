from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, func
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Mission(Base):
    __tablename__ = 'missions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    mission_id = Column(Integer, nullable=True)
    associated_mission = Column(Integer, ForeignKey('missions.id'), nullable=True)
    date = Column(DateTime, nullable=False)
    platform = Column(String, nullable=True)
    chassis = Column(String, nullable=True)
    customer = Column(String, nullable=True)
    site = Column(String, nullable=True)
    altitude_m = Column(String, nullable=True)
    speed_m_s = Column(String, nullable=True)
    spacing_m = Column(String, nullable=True)
    sky_conditions = Column(String, nullable=True)
    wind_knots = Column(Float, nullable=True)
    battery = Column(String, nullable=True)
    filesize_gb = Column(Float, nullable=True)
    is_test = Column(Boolean, default=False)
    issues_hw = Column(Text, nullable=True)
    issues_operator = Column(Text, nullable=True)
    issues_env = Column(Text, nullable=True)
    issues_sw = Column(Text, nullable=True)
    outcome = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    raw_metar = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())



# Optional: lookup tables for dropdown menus (not required unless you want to enforce domain values)

class Platform(Base):
    __tablename__ = 'platforms'
    name = Column(String, primary_key=True)


class Chassis(Base):
    __tablename__ = 'chassis'
    name = Column(String, primary_key=True)


class Customer(Base):
    __tablename__ = 'customers'
    name = Column(String, primary_key=True)


class Site(Base):
    __tablename__ = 'sites'
    name = Column(String, primary_key=True)


class Battery(Base):
    __tablename__ = 'batteries'
    name = Column(String, primary_key=True)


class IssuesSw(Base):
    __tablename__ = 'issues_sw'
    name = Column(String, primary_key=True)


class IssuesHw(Base):
    __tablename__ = 'issues_hw'
    name = Column(String, primary_key=True)


class IssuesOperator(Base):
    __tablename__ = 'issues_operator'
    name = Column(String, primary_key=True)


class IssuesEnv(Base):
    __tablename__ = 'issues_env'
    name = Column(String, primary_key=True)
