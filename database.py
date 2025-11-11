from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Aapke 'amruno_db' database se connect kar rahe hain
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:@localhost/amruno_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()