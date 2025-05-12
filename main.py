from bybit.BybitHelper import Bybit
from telegram.TelegramHelper import Telegram
from strategies.Strategy import MyStrategy
from time import sleep
import datetime as dt
from logs.logger import get_logger
from config import config
from session import active_users
from telegram.Bot import TelegramBot

if __name__ == '__main__':
    telegram = Telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_BOT_CHAT_ID)
    bot = TelegramBot(config.TELEGRAM_BOT_TOKEN)
    bybit = Bybit(config.BYBIT_API_KEY, config.BYBIT_API_SECRET, telegram)
    strategy = MyStrategy(bybit)
    logger = get_logger('main')

    bot.run() # Запускаем тг-бота

    # symbols = ['BNBUSDT']
    # max_pos = len(symbols) # Max positions qty

    # stop = False

    # telegram.send_telegram('Я включился!')

    # # Проверяем работоспособность API Bybit
    # if bybit.get_balance() == None:
    #     stop = True

    # while not stop:
    #     # Ждем окончания timeframe
    #     current_time = dt.datetime.now()
    #     if current_time.second < 59:
    #         print(f'Waiting {59 - current_time.second} seconds')
    #         logger.info(f'Waiting {59 - current_time.second} seconds')
    #         sleep(59 - current_time.second)
        
    #     try:
    #         pos = bybit.get_positions()
    #         print(f'Having {len(pos)} positions:')
    #         if len(pos) > 0:
    #             for symb, side_qty in pos.items():
    #                 print(f"{symb} -- {side_qty['side']} position, {side_qty['size']} tokens")

    #         if len(pos) > max_pos:
    #             logger.error(f'Too many positions {len(pos)} > {max_pos}')
    #             stop = True
    #             break

    #         # Checking every symbol from the symbols list
    #         for symbol in symbols:
    #             open_orders = bybit.get_open_orders(symbol)
    #             if len(open_orders) > 2:
    #                 logger.error(f'Too many orders ({open_orders}) for token {symbol}')
    #                 stop = True
    #                 break

    #             strategy.execute(symbol)
            
    #         # Если все проверили до конца timeframe - ждем
    #         current_time = dt.datetime.now()
    #         if current_time.second >= 59:
    #             sleep(1)
        
    #     except Exception as err:
    #         print(err)
    #         logger.error(f'Something is wrong in main. Watch out the terminal')
    #         stop = True
    #         break
    
    # telegram.send_telegram('Я выключился!')
