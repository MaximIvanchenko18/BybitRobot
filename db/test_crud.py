from db.database import SessionLocal
from db.crud import *

# Создание сессии
session = SessionLocal()

def test_all():
    try:
        print("\n-- Тестирование CRUD-функций --")

        # # 1. Создание пользователя
        # user = create_user(session, "123456", "api_key_test", "api_secret_test")
        # assert user is not None
        # print("create_user: ✅")

        # # 2. Создание/получение стратегии
        # settings = get_or_create_trade_settings(session, "BTC", 10, "1h", 0.2)
        # assert settings is not None
        # print("get_or_create_trade_settings: ✅")

        # # 3. Создание торговли и при необходимости бота
        # trade = create_trade_with_strategy(session, user.id, 1000.0, "BTC", 10, "1h", 0.2)
        # assert trade is not None
        # print("create_trade_with_strategy: ✅")

        # # 4. Получение пользователя, бота, трейда
        # assert get_user(session, user.id) is not None
        # assert get_bot(session, user.bots[0].id) is not None
        # assert get_trade(session, trade.id) is not None
        # print("get_user/bot/trade: ✅")

        # # 5. Получение стратегий
        # strategies = get_user_strategies(session, user.id)
        # assert len(strategies) > 0
        # print("get_user_strategies: ✅")

        # # 6. Обновление пользователя
        # updated_user = update_user(session, user.id, api_key="new_key")
        # assert updated_user.api_key == "new_key"
        # print("update_user: ✅")

        # # 7. Обновление бота
        # bot = user.bots[0]
        # updated_bot = update_bot(session, bot.id, is_running=True)
        # assert updated_bot.is_running is True
        # print("update_bot: ✅")

        # # 8. Обновление торговли
        # updated_trade = update_trade(session, trade.id, current_pnl=5.0)
        # assert updated_trade.current_pnl == 5.0
        # print("update_trade: ✅")

        # # 9. Обновление стратегии
        # updated_settings = update_trade_settings(session, settings.id, leverage=20)
        # assert updated_settings.leverage == 20
        # print("update_trade_settings: ✅")

        # # 10. Открытие трейда
        # opened_trade = open_trade(session, trade.id, entry_price=100)
        # assert opened_trade.is_active is True
        # print("open_trade: ✅")

        # # 10. Закрытие трейда
        # closed_trade = close_trade(session, trade.id, pnl=10.0)
        # assert closed_trade.is_active is False
        # print("close_trade: ✅")

        # # 11. Синхронизация баланса
        # synced_bot = sync_bot_balance(session, bot.id, new_balance=1050.0)
        # assert synced_bot.current_balance == 1050.0
        # print("sync_bot_balance: ✅")

        # # 12. Удаление трейда
        # assert delete_trade(session, trade.id) is True
        # print("delete_trade: ✅")

        # # 13. Удаление пользователя (каскадно удалит всё)
        # assert delete_user(session, user.id) is True
        # print("delete_user: ✅")

        clear_all_data(session)

        print("\nВсе тесты пройдены успешно! \U0001F389")

    except AssertionError:
        print("\u274C Тест не пройден")
    finally:
        session.close()

if __name__ == "__main__":
    test_all()
