import pandas_ta as ta
from bybit.BybitHelper import Bybit

# !!! ATTENTION !!!
# -------- 1 --------
# Если в стратегии вход по хай/лоу последней свечи - нужно увеличить/уменьшить цену-триггер на 1-2 пункта
# Это нужно из-за API Bybit, потому что если цена закрылась на хай/лоу, то цена "не пришла сверху/снизу" (triggerDirection)

myStrategyVolumes = {
    '1': (30, 77, 554),
    '60': (2.5e3, 6.9e3, 23.5e3)
}

class MyStrategy:
    def __init__(self, broker: Bybit, timeframe, leverage, depo_procent=100, own_trade=False):
        self.__broker = broker
        self.__takerFee = broker.get_fee_rates()[0]
        self.__own_trade = own_trade

        self.params = {
            "timeframe": timeframe,
            "volume_levels": myStrategyVolumes[timeframe],
            "ma_period": 10,
            "stochastic_params": (14, 3, 3),
            "window": 4,
            "rsi_levels": (30, 70),
            "max_loss_percent": 2,
            "leverage": leverage,
            'depo_part': depo_procent / 100
        }

        # Данные
        self.data = None
        # Индикаторы
        self.ma = None
        self.stochastic_k = None
        self.stochastic_d = None
        self.chaikin = None
        self.rsi = None

        # Интервал хорошего объема пробоя МА
        self.goodvolume = ((self.params['volume_levels'][0] + self.params['volume_levels'][1]) / 2, self.params['volume_levels'][2])

        # Определение цвета свечи
        self.bullish = lambda x: self.data['Open'].iloc[x] <= self.data['Close'].iloc[x]
        self.bearish = lambda x: self.data['Open'].iloc[x] > self.data['Close'].iloc[x]

    def graphic_signal(self, ind):
        if ((self.data['Open'].iloc[ind] <= self.ma.iloc[ind] and self.data['Close'].iloc[ind] > self.ma.iloc[ind] and # пробой
            self.goodvolume[0] <= self.data['Volume'].iloc[ind] <= self.goodvolume[1]) # на хорошем объеме
            or
            (ind < -2 and self.data['Open'].iloc[ind] <= self.ma.iloc[ind] and self.data['Close'].iloc[ind] > self.ma.iloc[ind] and # пробой
            self.bullish(ind + 1) and self.bullish(ind + 2))): # и следующие 2 свечи бычьи
            return 1 # long
        if (self.data['Open'].iloc[ind] >= self.ma.iloc[ind] and self.data['Close'].iloc[ind] < self.ma.iloc[ind] and # пробой
            self.goodvolume[0] <= self.data['Volume'].iloc[ind] <= self.goodvolume[1]): # на хорошем объеме
            return -1 # short
        return 0 # nothing

    # стоп - ближайший экстремум
    def define_stop_candle_index(self, side):
        ind = -1
        if side == 'long':
            while self.data['Low'].iloc[ind - 1] <= self.data['Low'].iloc[ind]:
                ind -= 1
        else: # short
            while self.data['High'].iloc[ind - 1] >= self.data['High'].iloc[ind]:
                ind -= 1
        return ind

    def calculate_order_size(self, order_price, stop_price, cur_pos=None):
        cash = self.__broker.get_availableWithdrawal_balance()
        if cash == None:
            return None
        
        # Вычитаем комиссии (в случае максимального входа)
        # https://www.bybit.com/ru-RU/help-center/article/Order-Cost-USDT-ContractUSDT_Perpetual_Contract
        # Вычитаем комиссию за открытие по тейкеру
        cash -= cash * self.params['leverage'] * self.__takerFee
        # Вычитаем комиссию за закрытие по тейкеру (берем шорт как худший вариант)
        cash -= cash * self.params['leverage'] * (1 + 1 / self.params['leverage']) * self.__takerFee

        if cur_pos != None:
            cur_margin = cur_pos['entryPrice'] * cur_pos['size'] / self.params['leverage']

            cur_pnl_by_order_price = cur_pos['size'] * (order_price - cur_pos['entryPrice'])
            if cur_pos['side'] == 'Sell':
                cur_pnl_by_order_price *= -1
            
            cash += cur_margin + cur_pnl_by_order_price

        cash *= self.params['depo_part'] # берем только торгуемый объем

        max_risk_qty = (cash*self.params['max_loss_percent']/100) / abs(order_price-stop_price)
        if max_risk_qty * order_price / self.params['leverage'] < cash:
            return max_risk_qty
        else:
            return cash * self.params['leverage'] / order_price

    def execute(self, symbol):
        self.data = self.__broker.klines(symbol, self.params['timeframe'])
        if self.data.empty:
            return None

        self.ma = ta.ema(close=self.data['Close'], length=self.params['ma_period'])
        stochastic = ta.stoch(high=self.data['High'], low=self.data['Low'], close=self.data['Close'],\
                                   k=self.params['stochastic_params'][0],\
                                   d=self.params['stochastic_params'][1],\
                                   smooth_k=self.params['stochastic_params'][2])
        self.stochastic_k = stochastic.iloc[:,0]
        self.stochastic_d = stochastic.iloc[:,1]
        self.chaikin = ta.adosc(high=self.data['High'], low=self.data['Low'], close=self.data['Close'], volume=self.data['Volume'],\
                                fast=3, slow=10)
        self.rsi = ta.rsi(close=self.data['Close'])

        # смотрим сигналы в пределах window свечей
        bull_signals = [0, 0, 0]
        bear_signals = [0, 0, 0]
        for i in range(self.params['window'], 0, -1):
            if (self.stochastic_k.iloc[-i - 1] <= self.stochastic_d.iloc[-i - 1] and
               self.stochastic_k.iloc[-i] > self.stochastic_d.iloc[-i]):
                bull_signals[1] = 1
                bear_signals[1] = 0
            elif (self.stochastic_k.iloc[-i - 1] >= self.stochastic_d.iloc[-i - 1] and
                 self.stochastic_k.iloc[-i] < self.stochastic_d.iloc[-i]):
                bear_signals[1] = 1
                bull_signals[1] = 0
                
            if self.chaikin.iloc[-i - 1] <= 0 and self.chaikin.iloc[-i] > 0:
                bull_signals[2] = 1
                bear_signals[2] = 0
            elif self.chaikin.iloc[-i - 1] >= 0 and self.chaikin.iloc[-i] < 0:
                bear_signals[2] = 1
                bull_signals[2] = 0
                
            if any(bull_signals) and self.graphic_signal(-i) == 1:
                bull_signals[0] = 1
                bear_signals[0] = 0
            if any(bear_signals) and self.graphic_signal(-i) == -1:
                bear_signals[0] = 1
                bull_signals[0] = 0

        if not self.__own_trade:
            if all(bull_signals) and self.data['Close'].iloc[-1] > self.ma.iloc[-1]:
                return 1
            elif all(bear_signals) and self.data['Close'].iloc[-1] < self.ma.iloc[-1]:
                return -1
            return 0
        # Если идем дальше - значит сами совершаем сделки
        
        # Если новый сигнал - снимаем открытые ордера
        open_orders = self.__broker.get_open_orders(symbol)
        if open_orders == None:
            return None
        if len(open_orders) > 2:
            return None
        if (all(bull_signals) and self.data['Close'].iloc[-1] > self.ma.iloc[-1]) and len(open_orders) > 0:
            self.__broker.cancel_all_symbol_orders(symbol)
        if (all(bear_signals) and self.data['Close'].iloc[-1] < self.ma.iloc[-1]) and len(open_orders) > 0:
            self.__broker.cancel_all_symbol_orders(symbol)
        
        positions = self.__broker.get_positions()
        if positions == None:
            return None
        
        price_step = self.__broker.get_price_and_qty_steps(symbol)[0] # шаг цены монеты
        if price_step == None:
            return None
        price_acc = len(str(price_step).split('.')[1])
        
        # Если не в позиции
        if not symbol in positions:
            # long
            if all(bull_signals) and self.data['Close'].iloc[-1] > self.ma.iloc[-1]:
                order_price = self.data['High'].iloc[-1] + price_step * 2
                stop_price = self.data['Low'].iloc[self.define_stop_candle_index('long')] - price_step * 2
                stop_price = round(stop_price, price_acc)

                size = self.calculate_order_size(order_price, stop_price)
                
                # Отправляем ордер
                self.__broker.place_stop_order(symbol=symbol, side='Buy', price=order_price,
                                               leverage=self.params['leverage'], qty=size, sl=stop_price)

            # short
            elif all(bear_signals) and self.data['Close'].iloc[-1] < self.ma.iloc[-1]:
                order_price = self.data['Low'].iloc[-1] - price_step * 2
                stop_price = self.data['High'].iloc[self.define_stop_candle_index('short')] + price_step * 2
                stop_price = round(stop_price, price_acc)

                size = self.calculate_order_size(order_price, stop_price)

                # Отправляем ордер
                self.__broker.place_stop_order(symbol=symbol, side='Sell', price=order_price,
                                               leverage=self.params['leverage'], qty=size, sl=stop_price)

        # Если в позиции
        else:
            # long
            if positions[symbol]['side'] == 'Buy':
                # если достигли КЗ RSI
                if self.rsi.iloc[-2] < self.params['rsi_levels'][1] and self.rsi.iloc[-1] >= self.params['rsi_levels'][1]:
                    # Закрываем открытый ордер если есть
                    if len(open_orders) > 0:
                        self.__broker.cancel_all_symbol_orders(symbol)
                    # Отправляем ордер
                    self.__broker.place_market_order(symbol=symbol, side='Sell', leverage=self.params['leverage'],
                                                     qty=positions[symbol]['size'])
                
                # если выход из КЗ RSI
                elif self.rsi.iloc[-2] >= self.params['rsi_levels'][1] and self.rsi.iloc[-1] < self.params['rsi_levels'][1]:
                    # Закрываем открытый ордер если есть
                    if len(open_orders) > 0:
                        self.__broker.cancel_all_symbol_orders(symbol)
                    # Отправляем ордер
                    self.__broker.place_stop_order(symbol=symbol, side='Sell', price=self.data['Low'].iloc[-1] - price_step * 2,
                                                   leverage=self.params['leverage'], qty=positions[symbol]['size'])
                
                # если переворот в short
                elif all(bear_signals) and self.data['Close'].iloc[-1] < self.ma.iloc[-1]:
                    order_price = self.data['Low'].iloc[-1] - price_step * 2
                    stop_price = self.data['High'].iloc[self.define_stop_candle_index('short')] + price_step * 2
                    stop_price = round(stop_price, price_acc)
                    
                    size = self.calculate_order_size(order_price, stop_price, positions[symbol])
                    
                    # Отправляем ордера на закрытие и открытие
                    self.__broker.place_stop_order(symbol=symbol, side='Sell', price=order_price,
                                                   leverage=self.params['leverage'], qty=positions[symbol]['size'], sl=stop_price)
                    self.__broker.place_stop_order(symbol=symbol, side='Sell', price=order_price,
                                                   leverage=self.params['leverage'], qty=size, sl=stop_price)
            
            # short
            else:
                # если достигли КЗ RSI
                if self.rsi.iloc[-2] > self.params['rsi_levels'][0] and self.rsi.iloc[-1] <= self.params['rsi_levels'][0]:
                    # Закрываем открытый ордер если есть
                    if len(open_orders) > 0:
                        self.__broker.cancel_all_symbol_orders(symbol)
                    # Отправляем ордер
                    self.__broker.place_market_order(symbol=symbol, side='Buy', leverage=self.params['leverage'],
                                                     qty=positions[symbol]['size'])
                
                # если выход из КЗ RSI
                elif self.rsi.iloc[-2] <= self.params['rsi_levels'][0] and self.rsi.iloc[-1] > self.params['rsi_levels'][0]:
                    # Закрываем открытый ордер если есть
                    if len(open_orders) > 0:
                        self.__broker.cancel_all_symbol_orders(symbol)
                    # Отправляем ордер
                    self.__broker.place_stop_order(symbol=symbol, side='Buy', price=self.data['High'].iloc[-1] + price_step * 2,
                                                   leverage=self.params['leverage'], qty=positions[symbol]['size'])
                
                # если переворот в long
                elif all(bull_signals) and self.data['Close'].iloc[-1] > self.ma.iloc[-1]:
                    order_price = self.data['High'].iloc[-1] + price_step * 2
                    stop_price = self.data['Low'].iloc[self.define_stop_candle_index('long')] - price_step * 2
                    stop_price = round(stop_price, price_acc)
                    
                    size = self.calculate_order_size(order_price, stop_price, positions[symbol])
                    
                    # Отправляем ордера на закрытие и открытие
                    self.__broker.place_stop_order(symbol=symbol, side='Buy', price=order_price,
                                                   leverage=self.params['leverage'], qty=positions[symbol]['size'], sl=stop_price)
                    self.__broker.place_stop_order(symbol=symbol, side='Buy', price=order_price,
                                                   leverage=self.params['leverage'], qty=size, sl=stop_price)
                    

class SimpleStrategy:
    def __init__(self, broker: Bybit, timeframe, leverage, depo_procent=100.0, own_trade=False):
        self.__broker = broker
        self.__takerFee = broker.get_fee_rates()[0]
        self.__own_trade = own_trade # совершает ли стратегия сделки сама или просто возвращает сигнал

        self.params = {
            "timeframe": timeframe,
            "ma_period": 10,
            "max_loss_percent": 2,
            "leverage": leverage,
            'depo_part': depo_procent / 100
        }

        # Данные
        self.data = None
        # Индикаторы
        self.ma = None

    # стоп - ближайший экстремум
    def define_stop_candle_index(self, side):
        ind = -1
        if side == 'long':
            while self.data['Low'].iloc[ind - 1] <= self.data['Low'].iloc[ind]:
                ind -= 1
        else: # short
            while self.data['High'].iloc[ind - 1] >= self.data['High'].iloc[ind]:
                ind -= 1
        return ind

    def calculate_order_size(self, order_price, stop_price, cur_pos=None):
        cash = self.__broker.get_availableWithdrawal_balance()
        if cash == None:
            return None
        
        # Вычитаем комиссии (в случае максимального входа)
        # https://www.bybit.com/ru-RU/help-center/article/Order-Cost-USDT-ContractUSDT_Perpetual_Contract
        # Вычитаем комиссию за открытие по тейкеру
        cash -= cash * self.params['leverage'] * self.__takerFee
        # Вычитаем комиссию за закрытие по тейкеру (берем шорт как худший вариант)
        cash -= cash * self.params['leverage'] * (1 + 1 / self.params['leverage']) * self.__takerFee

        if cur_pos != None:
            cur_margin = cur_pos['entryPrice'] * cur_pos['size'] / self.params['leverage']

            cur_pnl_by_order_price = cur_pos['size'] * (order_price - cur_pos['entryPrice'])
            if cur_pos['side'] == 'Sell':
                cur_pnl_by_order_price *= -1
            
            cash += cur_margin + cur_pnl_by_order_price
        
        cash *= self.params['depo_part'] # берем только торгуемый объем

        max_risk_qty = (cash*self.params['max_loss_percent']/100) / abs(order_price-stop_price)
        if max_risk_qty * order_price / self.params['leverage'] < cash:
            return max_risk_qty
        else:
            return cash * self.params['leverage'] / order_price
        
    def graphic_signal(self, ind):
        if (self.data['Close'].iloc[ind - 1] < self.ma.iloc[ind - 1] and
            self.data['Close'].iloc[ind] >= self.ma.iloc[ind]): # цена пробила вверх
            return 1 # long
        if (self.data['Close'].iloc[ind - 1] > self.ma.iloc[ind - 1] and
            self.data['Close'].iloc[ind] <= self.ma.iloc[ind]): # цена пробила вниз
            return -1 # short
        return 0 # nothing

    def execute(self, symbol):
        self.data = self.__broker.klines(symbol, self.params['timeframe'])
        if self.data.empty:
            return None

        self.ma = ta.ema(close=self.data['Close'], length=self.params['ma_period'])

        signal = self.graphic_signal(-1)

        if not self.__own_trade:
            return signal
        # Если идем дальше - значит сами совершаем сделки

        # Если новый сигнал - снимаем открытые ордера
        open_orders = self.__broker.get_open_orders(symbol)
        if open_orders == None:
            return None
        if len(open_orders) > 2:
            return None
        if (signal == -1 or signal == 1) and len(open_orders) > 0:
            self.__broker.cancel_all_symbol_orders(symbol)
        
        positions = self.__broker.get_positions()
        if positions == None:
            return None
        
        price_step = self.__broker.get_price_and_qty_steps(symbol)[0] # шаг цены монеты
        if price_step == None:
            return None
        price_acc = len(str(price_step).split('.')[1])
        
        # Если не в позиции
        if not symbol in positions:
            # long
            if signal == 1:
                order_price = self.data['High'].iloc[-1]
                stop_price = self.data['Low'].iloc[self.define_stop_candle_index('long')] - price_step * 2
                stop_price = round(stop_price, price_acc)

                size = self.calculate_order_size(order_price, stop_price)
                
                # Отправляем ордер
                self.__broker.place_market_order(symbol=symbol, side='Buy', leverage=self.params['leverage'], qty=size, sl=stop_price)

            # short
            elif signal == -1:
                order_price = self.data['Low'].iloc[-1]
                stop_price = self.data['High'].iloc[self.define_stop_candle_index('short')] + price_step * 2
                stop_price = round(stop_price, price_acc)

                size = self.calculate_order_size(order_price, stop_price)

                # Отправляем ордер
                self.__broker.place_market_order(symbol=symbol, side='Sell', leverage=self.params['leverage'], qty=size, sl=stop_price)

        # Если в позиции
        else:
            # long
            if positions[symbol]['side'] == 'Buy':
                # если переворот в short
                if signal == -1:
                    order_price = self.data['Low'].iloc[-1]
                    stop_price = self.data['High'].iloc[self.define_stop_candle_index('short')] + price_step * 2
                    stop_price = round(stop_price, price_acc)
                    
                    size = self.calculate_order_size(order_price, stop_price, positions[symbol])
                    
                    # Отправляем ордера на закрытие и открытие
                    self.__broker.place_market_order(symbol=symbol, side='Sell', leverage=self.params['leverage'], qty=positions[symbol]['size'], sl=stop_price)
                    self.__broker.place_market_order(symbol=symbol, side='Sell', leverage=self.params['leverage'], qty=size, sl=stop_price)
            
            # short
            else:
                # если переворот в long
                if signal == 1:
                    order_price = self.data['High'].iloc[-1]
                    stop_price = self.data['Low'].iloc[self.define_stop_candle_index('long')] - price_step * 2
                    stop_price = round(stop_price, price_acc)
                    
                    size = self.calculate_order_size(order_price, stop_price, positions[symbol])
                    
                    # Отправляем ордера на закрытие и открытие
                    self.__broker.place_market_order(symbol=symbol, side='Buy', leverage=self.params['leverage'], qty=positions[symbol]['size'], sl=stop_price)
                    self.__broker.place_market_order(symbol=symbol, side='Buy', leverage=self.params['leverage'], qty=size, sl=stop_price)
