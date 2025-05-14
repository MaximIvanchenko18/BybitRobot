from sqlalchemy.orm import Session
from db.models import User, TradeSettings, Trade, Bot
from typing import Optional, List, Dict
from sqlalchemy import text
from datetime import datetime
from logs.logger import get_logger

logger = get_logger('database')

def create_user(db: Session, telegram_id: str, api_key: str, api_secret: str) -> User:
    try:
        user = db.query(User).filter_by(telegram_id=telegram_id).first()
        if user:
            return user
        new_user = User(telegram_id=telegram_id, api_key=api_key, api_secret=api_secret)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as err:
        print(err)
        logger.error(f"Error while creating user with tg-id: {telegram_id}: {err}")
        return None

def create_bot(db: Session, user_id: int, current_balance: float) -> Bot:
    try:
        bot = db.query(Bot).filter_by(user_id=user_id).first()
        if bot:
            return bot
        new_bot = Bot(user_id=user_id, current_balance=current_balance)
        db.add(new_bot)
        db.commit()
        db.refresh(new_bot)
        return new_bot
    except Exception as err:
        print(err)
        logger.error(f"Error while creating bot for user: {user_id}: {err}")
        return None


def get_or_create_trade_settings(db: Session, coin_name: str, leverage: int, timeframe: str, depo_procent: float) -> TradeSettings:
    try:
        settings = db.query(TradeSettings).filter_by(
            coin_name=coin_name,
            leverage=leverage,
            timeframe=timeframe,
            depo_procent=depo_procent
        ).first()
        if settings:
            return settings
        new_settings = TradeSettings(
            coin_name=coin_name,
            leverage=leverage,
            timeframe=timeframe,
            depo_procent=depo_procent
        )
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings
    except Exception as err:
        print(err)
        logger.error(f"Error while getting/creating trade setting: {err}")
        return None

def create_trade_with_strategy(db: Session, user_id: int, current_balance: float, coin_name: str, leverage: int, timeframe: str, depo_procent: float) -> Trade:
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            raise ValueError("User not found")

        settings = get_or_create_trade_settings(db, coin_name, leverage, timeframe, depo_procent)

        existing_bot = db.query(Bot).filter_by(user_id=user_id).first()
        if not existing_bot:
            create_bot(db, user_id, current_balance)

        new_trade = Trade(
            user_id=user_id,
            strategy_id=settings.id
        )
        db.add(new_trade)
        db.commit()
        db.refresh(new_trade)
        return new_trade
    except Exception as err:
        print(err)
        logger.error(f"Error while creating trade for user {user_id}: {err}")
        return None
    
def get_user(db: Session, user_id: int) -> Optional[User]:
    try:
        return db.query(User).filter_by(id=user_id).first()
    except Exception as err:
        print(err)
        logger.error(f"Error while getting user {user_id}: {err}")
        return None
    
def get_bot(db: Session, bot_id: int) -> Optional[Bot]:
    try:
        return db.query(Bot).filter_by(id=bot_id).first()
    except Exception as err:
        print(err)
        logger.error(f"Error while getting bot {bot_id}: {err}")
        return None
    
def get_trade(db: Session, trade_id: int) -> Optional[Trade]:
    try:
        return db.query(Trade).filter_by(id=trade_id).first()
    except Exception as err:
        print(err)
        logger.error(f"Error while getting trade {trade_id}: {err}")
        return None

def get_user_strategies(db: Session, user_id: int) -> List[Dict]:
    try:
        trades = db.query(Trade).filter_by(user_id=user_id).all()
        strategy_ids = list(set([t.strategy_id for t in trades if t.strategy_id is not None]))
        strategies = db.query(TradeSettings).filter(TradeSettings.id.in_(strategy_ids)).all()
        return [s for s in strategies]
    except Exception as err:
        print(err)
        logger.error(f"Error while getting strategies for user {user_id}: {err}")
        return None
    
def update_user(db: Session, user_id: int, api_key: str=None, api_secret: str=None, created_at: datetime=None) -> Optional[User]:
    try:
        user = get_user(db, user_id)
        if not user:
            raise ValueError("User not found")
        if api_key:
            user.api_key = api_key
        if api_secret:
            user.api_secret = api_secret
        if created_at:
            user.created_at = created_at
        db.commit()
        db.refresh(user)
        return user
    except Exception as err:
        print(err)
        logger.error(f"Error while updating user {user_id}: {err}")
        return None
    
def update_bot(db: Session, bot_id: int, current_balance: float=None, all_time_pnl: float=None, is_running: bool=None) -> Optional[Bot]:
    try:
        bot = get_bot(db, bot_id)
        if not bot:
            raise ValueError("Bot not found")
        if current_balance:
            bot.current_balance = current_balance
        if all_time_pnl:
            bot.all_time_pnl = all_time_pnl
        if is_running:
            bot.is_running = is_running
        db.commit()
        db.refresh(bot)
        return bot
    except Exception as err:
        print(err)
        logger.error(f"Error while updating bot {bot_id}: {err}")
        return None
    
def update_trade(db: Session, trade_id: int, entry_price: float=None, current_pnl: float=None, is_active: bool=None, opened_at: datetime=None, closed_at: datetime=None) -> Optional[Trade]:
    try:
        trade = get_trade(db, trade_id)
        if not trade:
            raise ValueError("Trade not found")
        if entry_price:
            trade.entry_price = entry_price
        if current_pnl:
            trade.current_pnl = current_pnl
        if is_active:
            trade.is_active = is_active
        if opened_at:
            trade.opened_at = opened_at
        if closed_at:
            trade.closed_at = closed_at
        db.commit()
        db.refresh(trade)
        return trade
    except Exception as err:
        print(err)
        logger.error(f"Error while updating trade {trade_id}: {err}")
        return None

def update_trade_settings(db: Session, strategy_id: int, coin_name: str=None, leverage: int=None, timeframe: str=None, depo_procent: float=None) -> Optional[TradeSettings]:
    try:
        settings = db.query(TradeSettings).filter_by(id=strategy_id).first()
        if not settings:
            raise ValueError("Trading setting not found")
        if coin_name:
            settings.coin_name = coin_name
        if leverage:
            settings.leverage = leverage
        if timeframe:
            settings.timeframe = timeframe
        if depo_procent:
            settings.depo_procent = depo_procent
        db.commit()
        db.refresh(settings)
        return settings
    except Exception as err:
        print(err)
        logger.error(f"Error while updating trade setting {strategy_id}: {err}")
        return None
    
def delete_user(db: Session, user_id: int) -> bool:
    try:
        user = get_user(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True
    except Exception as err:
        print(err)
        logger.error(f"Error while deleting user {user_id}: {err}")
        return None

def delete_trade(db: Session, trade_id: int) -> bool:
    try:
        trade = get_trade(db, trade_id)
        if not trade:
            return False
        db.delete(trade)
        db.commit()
        return True
    except Exception as err:
        print(err)
        logger.error(f"Error while deleting trade {trade_id}: {err}")
        return None
    
def sync_bot_balance(db: Session, bot_id: int, new_balance: float) -> Optional[Bot]:
    try:
        bot = get_bot(db, bot_id)
        if not bot:
            raise ValueError("Bot not found")
        pnl_change = new_balance - bot.current_balance
        bot.all_time_pnl += pnl_change
        bot.current_balance = new_balance
        db.commit()
        db.refresh(bot)
        return bot
    except Exception as err:
        print(err)
        logger.error(f"Error while syncing balance for bot {bot_id}: {err}")
        return None
    
def open_trade(db: Session, trade_id: int, entry_price: float) -> Optional[Trade]:
    try:
        trade = get_trade(db, trade_id)
        if not trade or trade.is_active:
            return None
        trade.entry_price = entry_price
        trade.is_active = True
        trade.opened_at = datetime.now()
        db.commit()
        db.refresh(trade)
        return trade
    except Exception as err:
        print(err)
        logger.error(f"Error while closing trade {trade_id}: {err}")
        return None
    
def close_trade(db: Session, trade_id: int, pnl: float) -> Optional[Trade]:
    try:
        trade = get_trade(db, trade_id)
        if not trade or not trade.is_active:
            return None
        trade.current_pnl = pnl
        trade.is_active = False
        trade.closed_at = datetime.now()
        db.commit()
        db.refresh(trade)
        return trade
    except Exception as err:
        print(err)
        logger.error(f"Error while closing trade {trade_id}: {err}")
        return None
    
def clear_all_data(db: Session):
    try:
        db.query(Trade).delete()
        db.query(Bot).delete()
        db.query(User).delete()
        db.query(TradeSettings).delete()
        db.commit()

        # Сбросить последовательности (автоинкременты)
        db.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE bots_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE trades_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE trade_settings_id_seq RESTART WITH 1"))
        db.commit()

        logger.info(f"DB is successfully cleared")
        print("✅ Все записи из таблиц удалены")
    except Exception as err:
        db.rollback()
        logger.error(f"Error while clearing all data in DB: {err}")
        print(f"❌ Ошибка при удалении данных: {err}")
    finally:
        db.close()