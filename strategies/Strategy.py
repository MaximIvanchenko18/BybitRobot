from bybit.BybitHelper import Bybit
from db.session import DBSessionManager
from db.crud import *
from strategies.TechStrategy import SimpleStrategy
from telebot.types import Message

# В конце каждого ТФ нужно обновлять bot.current_balance и all_time_pnl и trade.current_pnl

class Strategy:
    def __init__(self, telegram_bot, user_id, strategy_id, only_tech=True):
        self.bot = telegram_bot
        self.user = {}
        self.strategy_params = {}
        self.only_tech = only_tech
        with DBSessionManager() as db:
            self.user = get_user(db, user_id)
            all_user_strategies = get_user_strategies(db, user_id)
            for strat in all_user_strategies:
                if strat['id'] == strategy_id:
                    self.strategy_params = strat
                    break
        
        self.broker = Bybit(self.user['api_key'], self.user['api_secret'], self.user['telegram_id'], self.bot)
        self.tech_strategy = SimpleStrategy(self.broker, self.strategy_params['timeframe'], self.strategy_params['leverage'], self.strategy_params['depo_procent'], own_trade=self.only_tech)

    def execute(self):
        # Проверка на доступ к бирже
        if self.broker.get_balance() == None:
            self.bot.send_message_to_user(self.user['telegram_id'], 'Произошла ошибка при обращении к Bybit! Робот принудительно остановлен!')

            message = Message() # заглушка, чтобы вызвать stop_bot
            message.chat = type("Chat", (), {"id": self.user['telegram_id']})
            self.bot.stop_bot(message)
            return
        
        tech_signal = self.tech_strategy.execute(symbol=self.strategy_params['coin_name'])
        if not self.only_tech and tech_signal != None:
            # Здесь вызываем ML стратегию
            pass
