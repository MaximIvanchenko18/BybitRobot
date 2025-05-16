from pybit.unified_trading import HTTP, WebSocket
import pandas as pd
from time import sleep
import datetime as dt
from logs.logger import get_logger

# timeframe 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, M, W
timeframe_match = {
    '1 мин': '1',
    '1 час': '60',
}

class Bybit:
    def __init__(self, api, secret, user_id=None, telegram_bot=None):
        self.__bot = telegram_bot
        self.__user_id = user_id
        self.__session = HTTP(api_key=api, api_secret=secret, testnet=False)
        self.__ws = None
        self.__logger = get_logger('bybit')
        self.is_connected = True

        if self.get_balance() != None:
            self.__ws = WebSocket(channel_type="private", api_key=api, api_secret=secret, testnet=False)
            self.start_order_ws_stream() # Запуск отслеживания ордеров через WebSocket
        else:
            self.is_connected = False

    def __del__(self):
        if self.is_connected:
            self.stop_ws_stream() # Остановка отслеживания ордеров через WebSocket

    def filled_order_callback(self, message):
        if not message['data']:
            return

        try:
            for order in message['data']:
                if order['orderStatus'] == "Filled" and order['rejectReason'] == "EC_NoError":
                    text = (
                        f"Исполнен {order['orderType']} ордер.\n"
                        f"Инструмент: {order['symbol'].split('-')[0]}.\n"
                        f"Направление: {order['side']}.\n"
                        f"Средняя цена исполнения: {order['avgPrice'] if order['avgPrice'] != "" else order['price']}.\n"
                        f"Количество: {order['cumExecQty']} ({order['cumExecValue']} USDT)."
                    )

                    # могут приходить на все ордера, даже когда не запущена стратегия
                    if self.__bot and self.__user_id:
                        self.__bot.send_message_to_user(self.__user_id, text)
                    else:
                        print(text)

            self.__logger.info('Successfully got info about filled orders')

        except Exception as err:
            print(err)
            self.__logger.error('Error in filled_order_callback')

    def start_order_ws_stream(self):
        try:
            self.__ws.order_stream(callback=self.filled_order_callback)
            self.__logger.info('Successfully activated order stream by Bybit WebSocket')
        except Exception as err:
            print(err)
            self.__logger.error('Cannot activate order stream by Bybit WebSocket')
    
    def stop_ws_stream(self):
        try:
            self.__ws.exit()
            self.__logger.info('Successfully stopped stream by Bybit WebSocket')
        except Exception as err:
            print(err)
            self.__logger.error('Cannot stop stream by Bybit WebSocket')

    # Getting balance on Bybit Derivatrives Asset (in USDT)
    def get_balance(self):
        try:
            resp = self.__session.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list'][0]['coin'][0]['walletBalance']

            self.__logger.info(f'Successfully got balance: {resp} USDT')
            return float(resp)
        
        except Exception as err:
            self.__logger.error('Cannot get balance')
            return None
        
    # Getting balance available for withdraw
    def get_availableWithdrawal_balance(self, symbol="USDT"):
        try:
            resp = self.__session.get_transferable_amount(coinName=symbol)['result']['availableWithdrawal']

            self.__logger.info(f'Successfully got availableWithdrawal balance: {resp}')
            return float(resp)
        
        except Exception as err:
            print(err)
            self.__logger.error('Cannot get availableWithdrawal balance')
            return None

    # Getting all available tickers from Derivatives market (like 'BTCUSDT', 'ETHUSDT', etc)
    def get_tickers(self):
        try:
            resp = self.__session.get_tickers(category="linear")['result']['list']

            symbols = []
            for elem in resp:
                if 'USDT' in elem['symbol'] and not 'USDC' in elem['symbol']:
                    symbols.append(elem['symbol'])
            
            self.__logger.info('Successfully got all available tickers')
            return symbols
        
        except Exception as err:
            print(err)
            self.__logger.error('Cannot get all available tickers')
            return None

    # Klines is the candles of some symbol (up to 1500 candles). Dataframe, last elem has [-1] index
    def klines(self, symbol, timeframe, limit=None, start_date=None):
        '''
            timeframe 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, M, W
        '''
        params = {'category': 'linear',
                  'symbol': symbol,
                  'interval': str(timeframe)}
        
        if limit == None:
            if start_date != None:
                start = int(dt.datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
                params['start'] = start
            else:
                limit = 200
        if limit != None:
            params['limit'] = limit
        
        try:
            resp = self.__session.get_kline(**params)['result']['list']

            resp = pd.DataFrame(resp)
            resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover']
            resp = resp.set_index('Time')
            resp = resp.astype(float)
            resp = resp[::-1]

            self.__logger.info(f'Successfully got klines for {symbol}')
            return resp
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get klines for {symbol}')
            return pd.DataFrame()

    # Getting your current positions. It returns symbols list with opened positions
    def get_positions(self):
        try:
            resp = self.__session.get_positions(
                category='linear',
                settleCoin='USDT'
            )['result']['list']

            pos = {}
            for elem in resp:
                pos[elem['symbol']] = {'side': elem['side'], 'entryPrice': float(elem['avgPrice']), 'size': float(elem['size'])}
            
            self.__logger.info(f'Successfully got positions. Quantity: {len(pos)}')
            return pos
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get positions')
            return None
        
    # Get open orders
    def get_open_orders(self, symbol=None):
        params = {'category': "linear",
                  'settleCoin': 'USDT',
                  'openOnly': 0}
        if symbol != None:
            params['symbol'] = symbol
        try:
            resp = self.__session.get_open_orders(**params)['result']['list']

            if symbol != None:
                self.__logger.info(f'Successfully got open orders for {symbol}')
            else:
                self.__logger.info('Successfully got all open orders')
            return resp
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get open orders')
            return None
        
    # Cancel order by Id
    def cancel_order_by_id(self, symbol, orderId):
        try:
            resp = self.__session.cancel_order(
                category='linear',
                symbol=symbol,
                orderId=orderId
            )

            self.__logger.info(f'Successfully cancelled order {orderId}')
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot cancel order {orderId}')

    # Cancel all symbol orders
    def cancel_all_symbol_orders(self, symbol):
        try:
            resp = self.__session.cancel_all_orders(
                category='linear',
                symbol=symbol
            )

            self.__logger.info(f'Successfully cancelled all orders for {symbol}')
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot cancel all orders for {symbol}')

    # Getting last N PnL (to check strategies performance)
    def get_last_pnl(self, limit=50):
        try:
            resp = self.__session.get_closed_pnl(category="linear", limit=limit)['result']['list']
            pnl = 0
            for elem in resp:
                pnl += float(elem['closedPnl'])

            self.__logger.info(f'Successfully got last {limit} PnL')
            return round(pnl, 4)
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get last {limit} PnL')
            return None

    # Getting current PnL.
    def get_current_pnl(self, symbol=None):
        try:
            resp = self.__session.get_positions(
                category="linear",
                symbol=symbol,
                settleCoin="USDT"
            )['result']['list']

            pnl = 0
            if symbol == None:
                for elem in resp:
                    pnl += float(elem['unrealisedPnl'])
                self.__logger.info(f'Successfully got current PnL: {pnl}')
            else:
                pnl = resp[0]['unrealisedPnl']
                self.__logger.info(f'Successfully got current PnL for {symbol}: {pnl}')
            
            return round(pnl, 4)
        
        except Exception as err:
            print(err)
            self.__logger.error('Cannot get current PnL')
            return None

    # Changing mode and leverage
    def set_mode(self, symbol, mode=1, leverage=1):
        try:
            resp = self.__session.switch_margin_mode(
                category='linear',
                symbol=symbol,
                tradeMode=str(mode),
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )

            if resp['retMsg'] == 'OK':
                if mode == 1:
                    self.__logger.info(f'Successfully changed margin mode to ISOLATED for {symbol}')
                if mode == 0:
                    self.__logger.info(f'Successfully changed margin mode to CROSS for {symbol}')
            else:
                self.__logger.warning(f'After changing margin mode for {symbol} got message: {resp['retMsg']}')
        
        except Exception as err:
            if '110026' in str(err):
                self.__logger.info(f'Margin mode is not changed for {symbol}')
            else:
                print(err)
                self.__logger.error(f'Cannot change margin mode for {symbol}')

    # Getting number of decimal digits for price and qty
    def get_price_and_qty_steps(self, symbol):
        try:
            resp = self.__session.get_instruments_info(
                category='linear',
                symbol=symbol
            )['result']['list'][0]

            tick = resp['priceFilter']['tickSize']
            if float(tick) < 0.99:
                tick = float(tick)
            else:
                tick = int(tick)
            
            qty = float(resp['lotSizeFilter']['qtyStep'])
            if float(qty) < 0.99:
                qty = float(qty)
            else:
                qty = int(qty)
            
            self.__logger.info(f'Successfully got steps for {symbol}: price - {tick} and lotSize - {qty}')
            return tick, qty
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get steps for {symbol}')
            return None, None
        
    # Get fee rates
    def get_fee_rates(self, symbol="BTCUSDT"):
        try:
            resp = self.__session.get_fee_rates(
                category='linear',
                symbol=symbol
            )['result']['list'][0]
            
            self.__logger.info(f'Successfully got fee rates for {symbol}: taker - {resp['takerFeeRate']}, maker - {resp['makerFeeRate']}')

            return float(resp['takerFeeRate']), float(resp['makerFeeRate'])
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get fee rates for {symbol}')
            return None, None
        
    # Get min order quantity
    def get_min_order_quantity(self, symbol):
        try:
            min_qty = self.__session.get_instruments_info(
                category='linear',
                symbol=symbol
            )['result']['list'][0]['lotSizeFilter']['minOrderQty']

            self.__logger.info(f'Successfully got min order quantity for {symbol}: {min_qty}')
            return float(min_qty)
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get min order quantity for {symbol}')
            return None

    # Get max available leverage
    def get_max_leverage(self, symbol):
        try:
            resp = self.__session.get_instruments_info(
                category="linear",
                symbol=symbol
            )['result']['list'][0]['leverageFilter']['maxLeverage']

            self.__logger.info(f'Successfully got max leverage for {symbol}: {resp}')
            return float(resp)
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get max leverage for {symbol}')
            return None

    # Set leverage
    def set_leverage(self, symbol, leverage=1):
        try:
            resp = self.__session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            if resp['retMsg'] == 'OK':
                self.__logger.info(f'Successfully changed leverage to {leverage} for {symbol}')
            else:
                self.__logger.warning(f'After changing leverage to {leverage} for {symbol} got message: {resp['retMsg']}')

        except Exception as err:
            if '110043' in str(err):
                self.__logger.info(f'Leverage is not changed to {leverage} for {symbol}')
            else:
                print(err)
                self.__logger.error(f'Cannot change leverage to {leverage} for {symbol}')

    # Get Market price
    def get_market_price(self, symbol):
        try:
            mark_price = self.__session.get_tickers(
                category='linear',
                symbol=symbol
            )['result']['list'][0]['lastPrice']
            
            self.__logger.info(f'Successfully got market price for {symbol}: {mark_price}')
            return float(mark_price)
        
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot get market price for {symbol}')
            return None

    # Placing order with Market price. Placing TP and SL as well
    def place_market_order(self, symbol, side, mode=1, leverage=1, qty=None, sl=None, tp=None):
        if qty == None:
            return
        
        self.set_leverage(symbol, leverage)
        # sleep(0.5)

        size_step = self.get_price_and_qty_steps(symbol)[1]
        if size_step == None:
            return
        
        # Приводим qty к необходимой точности
        qty = int(qty / size_step) * size_step
        if size_step < 1:
            size_precision = len(str(size_step).split('.')[1])
            qty = round(qty, size_precision)

        min_order_qty = self.get_min_order_quantity(symbol)
        if min_order_qty == None:
            return
        if qty < min_order_qty:
            self.__logger.warning(f'Order size is too small for {symbol}')
            return
        
        mark_price = self.get_market_price(symbol)
        if mark_price == None:
            return
        
        self.__logger.info(f'Start placing market {side} order for {symbol}. Mark price: {mark_price}')

        params = {'category': 'linear',
                  'symbol': symbol,
                  'orderType': 'Market',
                  'qty': str(qty),
                  'tpslMode': 'Full'}
        if tp != None:
            params['takeProfit'] = str(tp)
            params['tpOrderType'] = 'Market'
            params['tpTriggerBy'] = 'LastPrice'
        if sl != None:
            params['stopLoss'] = str(sl)
            params['slOrderType'] = 'Market'
            params['slTriggerBy'] = 'LastPrice'

        try:
            if side == 'Buy':
                params['side'] = 'Buy'
                resp = self.__session.place_order(**params)

                if resp['retMsg'] == 'OK':
                    self.__logger.info(f'Successfully placed market {side} order for {symbol}. Mark price: {mark_price}')
                    text = "Выставлен рыночный ордер на покупку.\n"
                else:
                    self.__logger.error(f'Error after placing market {side} order for {symbol}. Message: {resp['retMsg']}')
                    text = "ОШИБКА при выставлении рыночного ордера на покупку.\n"

            else: # Sell
                params['side'] = 'Sell'
                resp = self.__session.place_order(**params)

                if resp['retMsg'] == 'OK':
                    self.__logger.info(f'Successfully placed market {side} order for {symbol}. Mark price: {mark_price}')
                    text = "Выставлен рыночный ордер на продажу.\n"
                else:
                    self.__logger.error(f'Error after placing market {side} order for {symbol}. Message: {resp['retMsg']}')
                    text = "ОШИБКА при выставлении рыночного ордера на продажу.\n"

            text += (
                f"Инструмент: {symbol}.\n"
                f"Цена: {mark_price}.\n"
                f"Стоп-лосс: {sl if sl != None else '---'}.\n"
                f"Тейк-профит: {tp if tp != None else '---'}.\n"
                f"Количество: {qty} ({round(qty * mark_price, 4)} USDT)."
            )

            if self.__bot and self.__user_id:
                self.__bot.send_message_to_user(self.__user_id, text)
            else:
                print(text)
            
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot place market {side} order for {symbol}')
            raise Exception('Something is wrong with market order')

    def place_stop_order(self, symbol, side, price, triggerPrice=None, mode=1, leverage=1, qty=None, sl=None, tp=None):
        if qty == None:
            return
        
        self.set_leverage(symbol, leverage)
        # sleep(0.5)

        size_step = self.get_price_and_qty_steps(symbol)[1]
        if size_step == None:
            return

        # Приводим qty к необходимой точности
        qty = int(qty / size_step) * size_step
        if size_step < 1:
            size_precision = len(str(size_step).split('.')[1])
            qty = round(qty, size_precision)

        min_order_qty = self.get_min_order_quantity(symbol)
        if min_order_qty == None:
            return
        if qty < min_order_qty:
            self.__logger.warning(f'Order size is too small for {symbol}')
            return

        if triggerPrice == None:
            triggerPrice = price
        
        self.__logger.info(f'Start placing stop {side} order for {symbol}. Trigger price: {triggerPrice}')

        params = {'category': 'linear',
                  'symbol': symbol,
                  'orderType': 'Limit',
                  'qty': str(qty),
                  'price': str(price),
                  'triggerPrice': str(triggerPrice),
                  'triggerBy': 'LastPrice',
                  'tpslMode': 'Full'}
        if tp != None:
            params['takeProfit'] = str(tp)
            params['tpOrderType'] = 'Market'
            params['tpTriggerBy'] = 'LastPrice'
        if sl != None:
            params['stopLoss'] = str(sl)
            params['slOrderType'] = 'Market'
            params['slTriggerBy'] = 'LastPrice'

        try:
            if side == 'Buy':
                params['side'] = 'Buy'
                params['triggerDirection'] = 1 # цена придет снизу
                
                resp = self.__session.place_order(**params)

                if resp['retMsg'] == 'OK':
                    self.__logger.info(f'Successfully placed stop {side} order for {symbol}. Trigger price: {triggerPrice}')
                    text = "Выставлен стоп-ордер на покупку.\n"
                else:
                    self.__logger.error(f'Error after placing stop {side} order for {symbol}. Message: {resp['retMsg']}')
                    text = "ОШИБКА при выставлении стоп-ордера на покупку.\n"

            else: # Sell
                params['side'] = 'Sell'
                params['triggerDirection'] = 2 # цена придет сверху
                
                resp = self.__session.place_order(**params)

                if resp['retMsg'] == 'OK':
                    self.__logger.info(f'Successfully placed stop {side} order for {symbol}. Trigger price: {triggerPrice}')
                    text = "Выставлен стоп-ордер на продажу.\n"
                else:
                    self.__logger.error(f'Error after placing stop {side} order for {symbol}. Message: {resp['retMsg']}')
                    text = "ОШИБКА при выставлении стоп-ордера на продажу.\n"

            text += (
                f"Инструмент: {symbol}.\n"
                f"Триггер-цена: {triggerPrice}.\n"
                f"Цена: {price}.\n"
                f"Стоп-лосс: {sl if sl != None else '---'}.\n"
                f"Тейк-профит: {tp if tp != None else '---'}.\n"
                f"Количество: {qty} ({round(qty * price, 4)} USDT)."
            )

            if self.__bot and self.__user_id:
                self.__bot.send_message_to_user(self.__user_id, text)
            else:
                print(text)
            
        except Exception as err:
            print(err)
            self.__logger.error(f'Cannot place stop {side} order for {symbol}')
            raise Exception('Something is wrong with stop order')
