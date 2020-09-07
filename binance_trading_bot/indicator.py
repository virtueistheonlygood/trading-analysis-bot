from binance_trading_bot import utilities
import matplotlib.pyplot as plt
plt.style.use('classic')
import pandas as pd
import numpy as np

def rsi(candles, n):
    diff = candles['close'].diff(1)
    up = diff.where(diff > 0, 0.0)
    dn = -diff.where(diff < 0, 0.0)
    emaup = up.ewm(alpha=1/n, min_periods=0, adjust=False).mean()
    emadn = dn.ewm(alpha=1/n, min_periods=0, adjust=False).mean()
    rs = emaup / emadn
    rsi = pd.Series(np.where(emadn==0, 100, 100-(100/(1+rs))), index=candles['close'].index)
    try:
        for i in range(n+1):
            rsi[i] = None
    except Exception:
        pass
    return rsi

def sma(candles):
    sma = pd.DataFrame()
    sma['50'] = candles['close'].rolling(50).mean()
    sma['100'] = candles['close'].rolling(100).mean()
    sma['200'] = candles['close'].rolling(200).mean()
    return sma

def volume_profile(client, market, NUM_PRICE_STEP, TIME_FRAME_STEP, TIME_FRAME_DURATION):
    candles = utilities.get_candles(client, market,
                                    TIME_FRAME_STEP, TIME_FRAME_DURATION)
    priceMin = candles['close'].min()
    priceMax = candles['close'].max()
    priceStep = (priceMax-priceMin)/NUM_PRICE_STEP
    volumeProfile = pd.DataFrame(index=np.arange(NUM_PRICE_STEP), 
                                  columns=['price_min', 'price_max', 
                                           'price', 
                                           'buy_volume',
                                           'sell_volume'])
    volumeProfile['price_min'] = \
    [priceMin+(i-1)*priceStep for i in np.arange(1, NUM_PRICE_STEP+1)]
    volumeProfile['price_max'] = \
    [priceMin+i*priceStep for i in np.arange(1, NUM_PRICE_STEP+1)]
    volumeProfile['price'] = \
    .5*(volumeProfile['price_min']+volumeProfile['price_max'])
    volumeProfile['buy_volume'] = \
    [sum(candles\
         [volumeProfile['price_min'][i]<=candles['close']]\
         [candles['close']<=volumeProfile['price_max'][i]]['buyQuoteVolume']) \
    for i in np.arange(NUM_PRICE_STEP)]
    volumeProfile['sell_volume'] = \
    [sum(candles\
         [volumeProfile['price_min'][i]<=candles['close']]\
         [candles['close']<=volumeProfile['price_max'][i]]['sellQuoteVolume']) \
    for i in np.arange(NUM_PRICE_STEP)]
    volumeProfile['volume'] = volumeProfile['buy_volume']+volumeProfile['sell_volume']
    return volumeProfile

def bbands(candles):
    std = candles['close'].rolling(window=20).std()
    middleBB = candles['close'].rolling(20).mean()
    upperBB = pd.Series(middleBB + (2 * std))
    lowerBB = pd.Series(middleBB - (2 * std))
    bollingerBands = pd.DataFrame()
    bollingerBands['middle_band'] = middleBB
    bollingerBands['upper_band'] = upperBB
    bollingerBands['lower_band'] = lowerBB
    bollingerBands['std'] = std
    return bollingerBands

def volatility_stop(candles, n, m): 
    VStop = pd.DataFrame()
    VStop['H-L'] = abs(candles['high']-candles['low'])
    VStop['H-PC'] = abs(candles['high']-candles['close'].shift(1))
    VStop['L-PC'] = abs(candles['low']-candles['close'].shift(1))
    VStop['TR'] = VStop[['H-L','H-PC','L-PC']].max(axis=1)
    VStop['ATR'] = np.nan
    VStop.ix[n-1,'ATR'] = VStop['TR'][:n-1].mean()
    for i in range(n,len(VStop)):
        VStop['ATR'][i] = (VStop['ATR'][i-1]*(n-1)+ VStop['TR'][i])/n
    VStop['support'] = candles['close']-m*VStop['ATR']
    VStop['resistance'] = candles['close']+m*VStop['ATR']
    i = VStop.index[0]
    while i<=VStop.index[-1]:
        try:
            if VStop['support'][i-1]>=0:
                if candles['close'][i]>=VStop['support'][i-1]:
                    VStop['support'][i] = max(VStop['support'][i-1], VStop['support'][i])
                else:
                    VStop['support'][i] = np.nan
        except Exception:
            pass
        try:
            if VStop['resistance'][i-1]>=0:
                if candles['close'][i]<=VStop['resistance'][i-1]:
                    VStop['resistance'][i] = min(VStop['resistance'][i-1], VStop['resistance'][i])
                else:
                    VStop['resistance'][i] = np.nan
        except Exception:
            pass
        i = i+1
    VStop = VStop[['support', 'resistance', 'ATR']]
    return VStop

