
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import time
from .serializers import SymbolSerializer
from .models import *
from django.shortcuts import render

from django.shortcuts import render

def forex_analysis_gui(request):
    return render(request, 'trading_app/forex_analysis_gui.html')


mt5.initialize()

class ForexAnalysisView(APIView):
    def get(self, request, *args, **kwargs):
        symbols = mt5.symbols_get()
        if symbols is None:
            return Response({"error": "Failed to fetch symbols"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        forex_symbols = [s.name for s in symbols if "Forex" in s.path and s.name.endswith(
            ('USD', 'EUR', 'JPY', 'GBP', 'AUD', 'NZD', 'CAD', 'CHF'))]
        
        return Response({"symbols": forex_symbols}, status=status.HTTP_200_OK)

class SymbolAnalysisView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = SymbolSerializer(data=request.data)
        if serializer.is_valid():
            symbol = serializer.validated_data['symbol']
            
            data = fetch_historical_data(symbol)
            if data is None:
                return Response({"error": f"Failed to fetch historical data for {symbol}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            sl_price, tp_price = calculate_sl_tp(symbol, volume=0.05, order_type=0)  # Example volume and order_type
            kvo, signal, hist = klinger_volume_oscillator(data, symbol)
            response_data = {
                "symbol": symbol,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "kvo": kvo.iloc[-1] if kvo is not None else None,
                "signal": signal.iloc[-1] if signal is not None else None,
                "hist": hist.iloc[-1] if hist is not None else None
            }
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def fetch_historical_data(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
    if rates is not None:
        return pd.DataFrame(rates)
    else:
        return None

def calculate_sl_tp(symbol, volume, order_type, atr_period=14):
    try:
        support, resistance = calculate_support_resistance(symbol, mt5.TIMEFRAME_H1)
        atr = calculate_atr(symbol, mt5.TIMEFRAME_H1, atr_period)
        bid_price = mt5.symbol_info_tick(symbol).bid
        ask_price = mt5.symbol_info_tick(symbol).ask

        sl_distance = atr if atr is not None else 0
        tp_distance = atr if atr is not None else 0

        if order_type == 0:
            sl_price = bid_price - sl_distance
            tp_price = ask_price + tp_distance
        else:
            sl_price = ask_price + sl_distance
            tp_price = bid_price - tp_distance

        return sl_price, tp_price
    except Exception as e:
        print(f"An error occurred while calculating dynamic SL/TP for {symbol}: {e}")
        return None, None

def klinger_volume_oscillator(data, symbol, fast_length=35, slow_length=50, signal_smoothing_type="EMA", signal_smoothing_length=16):
    try:
        volume = data["tick_volume"]
        high = data["high"]
        low = data["low"]
        close = data["close"]
    except KeyError as e:
        print(f"Error accessing required columns in data for {symbol}: {e}")
        return None, None, None

    if volume is None:
        print("Unable to retrieve volume data.")
        return pd.Series(), pd.Series(), pd.Series()

    mom = data["close"].diff()
    trend = np.zeros(len(data))
    trend[0] = 0.0

    for i in range(1, len(data)):
        if np.isnan(trend[i - 1]):
            trend[i] = 0
        else:
            if mom[i] > 0:
                trend[i] = 1
            elif mom[i] < 0:
                trend[i] = -1
            else:
                trend[i] = trend[i - 1]

    dm = data["high"] - data["low"]
    cm = np.zeros(len(data))
    cm[0] = 0.0

    for i in range(1, len(data)):
        if np.isnan(cm[i - 1]):
            cm[i] = 0.0
        else:
            if trend[i] == trend[i - 1]:
                cm[i] = cm[i - 1] + dm[i]
            else:
                cm[i] = dm[i] + dm[i - 1]

    vf = np.zeros(len(data))
    for i in range(len(data)):
        if cm[i] != 0:
            vf[i] = 100 * volume[i] * trend[i] * abs(2 * dm[i] / cm[i] - 1)

    fast_length = int(fast_length)
    slow_length = int(slow_length)
    kvo = pd.Series(vf).ewm(span=fast_length).mean() - pd.Series(vf).ewm(span=slow_length).mean()

    if signal_smoothing_type == "EMA":
        signal = kvo.ewm(span=signal_smoothing_length).mean()
    else:
        signal = kvo.rolling(window=signal_smoothing_length).mean()

    hist = kvo - signal
    return kvo, signal, hist

def calculate_atr(symbol, timeframe, atr_period):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, atr_period + 1)
    if rates is None:
        return None

    high_prices = np.array([x['high'] for x in rates])
    low_prices = np.array([x['low'] for x in rates])
    close_prices = np.array([x['close'] for x in rates])

    true_ranges = np.maximum(high_prices[1:] - low_prices[1:], np.abs(high_prices[1:] - close_prices[:-1]),
                              np.abs(low_prices[1:] - close_prices[:-1]))
    atr = np.mean(true_ranges)
    return atr

def calculate_support_resistance(symbol, timeframe, atr_period=14):
    pivot, r1, s1, r2, s2 = calculate_pivots(symbol, timeframe)
    atr = calculate_atr(symbol, timeframe, atr_period)

    support = pivot - 1.5 * atr
    resistance = pivot + 1.3 * atr
    return support, resistance

def calculate_pivots(symbol, timeframe):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 10)
    if rates is None or len(rates) < 1:
        return None, None, None, None, None

    high_prices = np.array([x['high'] for x in rates])
    low_prices = np.array([x['low'] for x in rates])
    close_prices = np.array([x['close'] for x in rates])

    pivot = (high_prices[0] + low_prices[0] + close_prices[0]) / 3
    r1 = 2 * pivot - low_prices[0]
    s1 = 2 * pivot - high_prices[0]
    r2 = pivot + (high_prices[0] - low_prices[0])
    s2 = pivot - (high_prices[0] - low_prices[0])
    return pivot, r1, s1, r2, s2


