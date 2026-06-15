"""
数据库会话管理
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# 根据数据库类型配置连接参数
_is_sqlite = "sqlite" in DATABASE_URL
_connect_args = {"check_same_thread": False} if _is_sqlite else {"charset": "utf8mb4"}
_pool_args = {} if _is_sqlite else {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_pool_args)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if _is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
