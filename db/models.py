# alembic revision --autogenerate -m "COMMENT"
# alembic upgrade head
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy import event
from sqlalchemy.orm import Session

Base = declarative_base()

# --- Пользователи ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    api_key = Column(String, nullable=False)
    api_secret = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), server_default=func.now(), nullable=False)

    bots = relationship("Bot", back_populates="user", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")

# --- Боты ---
class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    current_balance = Column(Float, nullable=False, default=0.0)
    all_time_pnl = Column(Float, nullable=False, default=0.0)
    is_running = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="bots")

# --- Параметры торговли ---
class TradeSettings(Base):
    __tablename__ = "trade_settings"

    id = Column(Integer, primary_key=True)
    coin_name = Column(String, nullable=False)
    leverage = Column(Integer, nullable=False)
    timeframe = Column(String, nullable=False)
    depo_procent = Column(Float, nullable=False)

    trades = relationship("Trade", back_populates="settings")

# --- Торговли ---
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("trade_settings.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    entry_price = Column(Float, nullable=True)
    current_pnl = Column(Float, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="trades")
    settings = relationship("TradeSettings", back_populates="trades")

@event.listens_for(Session, "after_flush")
def delete_unused_strategies_after_flush(session, flush_context):
    to_check = set()

    # Найти все удалённые объекты Trade
    for instance in session.deleted:
        if isinstance(instance, Trade) and instance.strategy_id:
            to_check.add(instance.strategy_id)

    for strategy_id in to_check:
        count = session.query(Trade).filter_by(strategy_id=strategy_id).count()
        if count == 0:
            strategy = session.query(TradeSettings).get(strategy_id)
            if strategy:
                session.delete(strategy)
