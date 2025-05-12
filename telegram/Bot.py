from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config
from logs.logger import get_logger
from session import active_users

class TelegramBot:
    def __init__(self, token):
        self.bot = TeleBot(token)
        self.logger = get_logger('telegramBot')
        self.available_tickers = config.AVAILABLE_TICKERS
        self.available_timeframes = config.AVAILABLE_TIMEFRAMES
        self.user_state = {}
        self.temp_strategy_data = {}

        # Команды
        self.bot.message_handler(commands=['start'])(self.start_handler)
        self.bot.message_handler(commands=['main'])(self.go_main_menu)
        self.bot.message_handler(commands=['help'])(self.send_help)

        # Кнопки
        self.bot.callback_query_handler(func=lambda call: call.data == "connect_exchange")(self.connect_exchange)
        self.bot.callback_query_handler(func=lambda call: call.data == "confirm_API")(self.confirm_api_keys)
        self.bot.callback_query_handler(func=lambda call: call.data == "rewrite_API")(self.connect_exchange)

        self.bot.callback_query_handler(func=lambda call: call.data == "set_new_strategy")(self.set_new_strategy)
        self.bot.message_handler(func=lambda msg: msg.text in self.available_tickers)(self.set_coin)
        self.bot.message_handler(func=lambda msg: msg.text in self.available_timeframes)(self.set_timeframe)
        self.bot.callback_query_handler(func=lambda call: call.data == "save_strategy")(self.save_strategy)
        self.bot.callback_query_handler(func=lambda call: call.data == "discard_strategy_changes")(self.go_main_menu_callback)

        self.bot.callback_query_handler(func=lambda call: call.data == "saved_strategies_list")(self.show_strategies)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("strategy_"))(self.handle_strategy_action)
        self.bot.callback_query_handler(func=lambda call: call.data.startswith("select_strategy_"))(self.select_strategy_action)
        self.bot.message_handler(func=lambda msg: msg.text == "❌ Остановить робота")(self.stop_bot)

        # Общий обработчик
        self.bot.message_handler(func=lambda msg: True)(self.handle_user_input)

    def start_handler(self, message):
        try:
            user_id = message.chat.id
            self.user_state[user_id] = {}
            self.temp_strategy_data[user_id] = {}
            
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🔐 Подключиться к бирже", callback_data="connect_exchange"))

            self.bot.send_message(message.chat.id, "Привет! Я бот для торговли на Bybit.\nНужно подключиться к аккаунту на Bybit, чтобы начать:", reply_markup=keyboard)
            self.logger.info(f'New user started: {message.chat.id}')
        except Exception as err:
            print(err)
            self.logger.error(f"Error while starting bot for user {message.chat.id}: {err}")

    def connect_exchange(self, call):
        try:
            self.bot.answer_callback_query(call.id)  # убирает загрузку
            self.user_state[call.message.chat.id] = {'step': 'awaiting_api_key'}
            self.bot.send_message(call.message.chat.id, "Введите API ключ от Bybit:", reply_markup=types.ReplyKeyboardRemove())
        except Exception as err:
            print(err)
            self.logger.error(f"Error while connecting to Bybit for user {call.message.chat.id}: {err}")

    def confirm_api_keys(self, call):
        try:
            self.bot.answer_callback_query(call.id)  # убирает загрузку
            state = self.user_state.get(call.message.chat.id, {})
            # TODO: здесь будет проверка ключей через Bybit API
            valid = True  # Заглушка

            if valid:
                state['verified'] = True
                self.bot.send_message(call.message.chat.id, "✅ Подключение прошло успешно!")
                self.logger.info(f'New user registered: {call.message.chat.id}')
                self.go_main_menu(call.message)
            else:
                self.bot.send_message(call.message.chat.id, "❌ Ошибка подключения. Введите ключи заново.")
                self.connect_exchange(call.message)
        except Exception as err:
            print(err)
            self.logger.error(f"Error while confirming API keys for user {call.message.chat.id}: {err}")

    def go_main_menu(self, message):
        try:
            user_id = message.chat.id
            state = self.user_state.get(user_id, {})

            if not state.get('verified') or state.get('verified') == False:
                self.bot.send_message(user_id, "❌ Сначала подключитесь к Bybit!")
                return

            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("➕ Задать параметры новой стратегии", callback_data="set_new_strategy"))
            # TODO: если есть стратегии → добавить кнопку "📂 Список сохранённых стратегий"
            keyboard.add(InlineKeyboardButton("📂 Список сохранённых стратегий", callback_data="saved_strategies_list"))

            self.bot.send_message(user_id, "Главное меню:", reply_markup=keyboard)
            self.user_state[user_id]['step'] = 'main_menu'
        except Exception as err:
            print(err)
            self.logger.error(f"Error in main menu for user {message.chat.id}: {err}")

    def go_main_menu_callback(self, call):
        self.bot.answer_callback_query(call.id)  # убирает загрузку
        self.go_main_menu(call.message)

    def send_help(self, message):
        text = (
            f"📘 Команды:\n"
            f"/start — Полный перезапуск робота с нуля (до введения API ключей)\n"
            f"/main — Главное меню (создание новых и выбор уже созданных Вами стратегий)\n"
            f"/help — Вызов текущей инструкции"
        )

        self.bot.send_message(message.chat.id, text)

    def set_new_strategy(self, call):
        try:
            self.bot.answer_callback_query(call.id)  # убирает загрузку
            self.temp_strategy_data[call.message.chat.id] = {'id': -1}
            self.user_state[call.message.chat.id]['step'] = 'awaiting_coin'

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            row_width = 6
            for i in range(0, len(self.available_tickers), row_width):
                keyboard.row(*[types.KeyboardButton(btn) for btn in self.available_tickers[i:i+row_width]])

            self.bot.send_message(call.message.chat.id, "Выберите валютную пару:", reply_markup=keyboard)
        except Exception as err:
            print(err)
            self.logger.error(f"Error after hitting new strategy for user {call.message.chat.id}: {err}")

    def set_coin(self, message):
        self.temp_strategy_data[message.chat.id]['coin'] = message.text
        self.user_state[message.chat.id]['step'] = 'awaiting_leverage'

        self.bot.send_message(message.chat.id, "Введите плечо (например, 5):", reply_markup=types.ReplyKeyboardRemove())

    def set_timeframe(self, message):
        self.temp_strategy_data[message.chat.id]['timeframe'] = message.text
        self.user_state[message.chat.id]['step'] = 'awaiting_percent'

        self.bot.send_message(message.chat.id, "Введите торгуемый процент от депозита (1-100). Желательно, чтобы он составлял не менее 100$:", reply_markup=types.ReplyKeyboardRemove())

    def save_strategy(self, call):
        self.bot.answer_callback_query(call.id)  # убирает загрузку
        user_id = call.message.chat.id
        strat = self.temp_strategy_data[user_id]
        strat_id = strat.get('id', -1)

        if strat_id == -1: # Новая стратегия
            pass # TODO: сохранить новую стратегию в БД
        else: # Изменение существующей
            pass # TODO: изменить стратегию в БД

        self.bot.send_message(user_id, f"Стратегия сохранена!", reply_markup=types.ReplyKeyboardRemove())
        self.logger.info(f"Strategy saved for user {user_id}: {strat}")

        self.go_main_menu(call.message)

    def show_strategies(self, call):
        self.bot.answer_callback_query(call.id)  # убирает загрузку
        # Заглушка получения стратегий пользователя
        user_id = call.message.chat.id
        strategies = [
            {'id': 1, 'coin': 'BNBUSDT', 'lev': 4, 'tf': '1м', 'pct': 50},
            {'id': 2, 'coin': 'BNBUSDT', 'lev': 3, 'tf': '1ч', 'pct': 30},
        ]  # TODO: заменить на реальные данные из БД

        keyboard = InlineKeyboardMarkup()

        for strat in strategies:
            name = f"Стратегия №{strat['id']} ({strat['coin']}, {strat['lev']}lev, {strat['tf']}, {strat['pct']}%)"
            callback_data = f"select_strategy_{strat['id']}"
            keyboard.add(InlineKeyboardButton(name, callback_data=callback_data))

        self.bot.send_message(user_id, "Выберите стратегию:", reply_markup=keyboard)

    def select_strategy_action(self, call):
        self.bot.answer_callback_query(call.id)  # убирает загрузку
        user_id = call.message.chat.id
        strat_id = int(call.data.replace("select_strategy_", ""))

        self.user_state[user_id]['step'] = 'strategy_menu'
        self.user_state[user_id]['selected_strategy'] = strat_id

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("▶️ Запустить", callback_data=f"strategy_run_{strat_id}"),
            InlineKeyboardButton("✏️ Изменить", callback_data=f"strategy_edit_{strat_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"strategy_delete_{strat_id}")
        )

        self.bot.send_message(user_id, f"Выбрана стратегия №{strat_id}. Что хотите сделать?", reply_markup=kb)

    def handle_strategy_action(self, call):
        self.bot.answer_callback_query(call.id)  # убирает загрузку
        user_id = call.message.chat.id

        if call.data.startswith("strategy_run_"):
            strat_id = int(call.data.replace("strategy_run_", ""))

            # 🟡 Заглушка запуска
            active_users[user_id] = strat_id

            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.KeyboardButton("❌ Остановить робота"))

            self.logger.info(f'Bot started working for user: {call.message.chat.id}')
            self.bot.send_message(user_id, f"✅ Робот запущен по стратегии №{strat_id}", reply_markup=keyboard)

        elif call.data.startswith("strategy_edit_"):
            strat_id = int(call.data.replace("strategy_edit_", ""))

            self.user_state[user_id]['step'] = 'awaiting_coin'
            self.temp_strategy_data[user_id] = {'id': strat_id}
            
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            row_width = 6
            for i in range(0, len(self.available_tickers), row_width):
                keyboard.row(*[types.KeyboardButton(btn) for btn in self.available_tickers[i:i+row_width]])

            self.bot.send_message(user_id, "Выберите новую валютную пару:", reply_markup=keyboard)

        elif call.data.startswith("strategy_delete_"):
            strat_id = int(call.data.replace("strategy_delete_", ""))

            # 🟡 Заглушка удаления

            self.bot.send_message(user_id, f"🗑 Стратегия №{strat_id} удалена")
            self.go_main_menu(call.message)

    def stop_bot(self, message):
        try:
            user_id = message.chat.id

            del active_users[user_id]
            self.logger.info(f'Bot stopped working for user: {message.chat.id}')
            self.bot.send_message(user_id, "Робот остановлен!", reply_markup=types.ReplyKeyboardRemove())
        except Exception as err:
            print(err)
            self.logger.error('Error while trying to stop robot.')

        self.go_main_menu(message)

    def handle_user_input(self, message):
        state = self.user_state.get(message.chat.id, {}).get('step')
        user_id = message.chat.id

        if state == 'awaiting_api_key':
            self.user_state[user_id]['api_key'] = message.text.strip()
            self.user_state[user_id]['step'] = 'awaiting_api_secret'

            self.bot.send_message(user_id, "Теперь введите API секрет:")
        elif state == 'awaiting_api_secret':
            self.user_state[user_id]['api_secret'] = message.text.strip()

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_API"),
                InlineKeyboardButton("🔁 Ввести заново", callback_data="rewrite_API")
            )

            self.bot.send_message(user_id, "Подтвердите введенные данные:", reply_markup=keyboard)
        elif state == 'awaiting_leverage':
            if message.text.strip().isdigit() and int(message.text.strip()) > 0:
                leverage = int(message.text.strip())
                max_leverage = 100 # !!! Нужно взять через Bybit
                if leverage <= max_leverage:
                    self.temp_strategy_data[user_id]['leverage'] = int(message.text.strip())
                    self.user_state[user_id]['step'] = 'awaiting_timeframe'

                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    row_width = 6
                    for i in range(0, len(self.available_timeframes), row_width):
                        keyboard.row(*[types.KeyboardButton(btn) for btn in self.available_timeframes[i:i+row_width]])

                    self.bot.send_message(user_id, "Выберите таймфрейм:", reply_markup=keyboard)
                else:
                    self.bot.send_message(user_id, f"❌ Введите число от 1 до {max_leverage}.")
            else:
                self.bot.send_message(user_id, "❌ Введите корректное число для плеча.")
        elif state == 'awaiting_percent':
            if message.text.strip().isdigit():
                percent = int(message.text.strip())
                if 1 <= percent <= 100:
                    self.temp_strategy_data[user_id]['percent'] = percent

                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(
                        InlineKeyboardButton("💾 Сохранить", callback_data="save_strategy"),
                        InlineKeyboardButton("❌ Отменить", callback_data="discard_strategy_changes")
                    )

                    self.bot.send_message(user_id, "Готово. Сохранить стратегию?", reply_markup=keyboard)
                else:
                    self.bot.send_message(user_id, "❌ Введите число от 1 до 100.")
            else:
                self.bot.send_message(user_id, "❌ Введите корректное число для процента.")
        else:
            self.bot.send_message(user_id, "Неизвестная команда. Используйте кнопки для действий.")

    def send_message_to_user(self, chat_id, text):
        try:
            self.bot.send_message(chat_id, text)
            self.logger.info(f"Sent message to user {chat_id}")
        except Exception as err:
            print(err)
            self.logger.error(f"Failed to send message to {chat_id}: {err}")

    def run(self):
        try:
            print("Telegram-бот запущен...")
            self.logger.info(f'Telegram-bot is activated!')
            self.bot.polling(none_stop=True)
        except Exception as err:
            print(err)
            self.logger.error('Cannot activate Telegram-bot')
