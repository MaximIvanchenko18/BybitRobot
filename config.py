import os
from dotenv import load_dotenv

# Загрузить переменные из .env
load_dotenv()

class Config:
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_BOT_CHAT_ID = os.getenv('TELEGRAM_BOT_CHAT_ID')

    # Available Trade Params
    AVAILABLE_TICKERS = ['BNBUSDT']
    AVAILABLE_TIMEFRAMES = ['1 мин', '1 час']

# Экспорт конфигурации
config = Config()