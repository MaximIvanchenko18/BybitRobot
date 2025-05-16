# docker-compose up -d
# PGADMIN - http://localhost:5050/
from time import sleep
import datetime as dt
from logs.logger import get_logger
from global_strategies import active_strategies
from config import config
from telegram.Bot import TelegramBot
from threading import Thread

if __name__ == '__main__':
    logger = get_logger('main')
    bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)

    # Запускаем бота в отдельном потоке
    Thread(target=bot.run, daemon=True).start()

    # bot.run() # Запускаем тг-бота

    stop = False
    while not stop:
        try:
            # Ждем окончания минуты
            current_time = dt.datetime.now()
            if current_time.second < 59:
                print(f'Waiting {59 - current_time.second} seconds')
                logger.info(f'Waiting {59 - current_time.second} seconds')
                sleep(59 - current_time.second)
        
            for strategy in active_strategies.values():
                strategy.execute()
            
            # Если все проверили до конца timeframe - ждем
            current_time = dt.datetime.now()
            if current_time.second >= 59:
                sleep(1)
        
        except Exception as err:
            print(err)
            logger.error(f'Something is wrong in main. Watch out the terminal')
            stop = True
            break

# Создаем список из объектов Strategy (у каждого user_id и все введенные параметры)
# Внутри try проходим по всем объектам (хочется асинхронно) и выполняем execute()
# Внутри execute() initial_check (базовые проверки, которые сейчас в try)
# Далее условия тех анализа
# Если выбрано еще и ML, то передаем сигнал тех анализа в блок ML
# Внутри блока ML берем еще предсказания LSTM и инференс RL
