from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.config import SQLALCHEMY_DATABASE_URL

# Создание движка
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Локальная сессия для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
