import numpy as np
import pandas as pd

def get_market_list(client, *args):
    marketList = pd.DataFrame(client.get_products()['data'])
    if len(args)>0:
        quoteBase = args[0]
        marketList = marketList[marketList['quoteAsset']==quoteBase]
    marketList['volume_24h'] = marketList['tradedMoney']
    marketList = marketList[['symbol', 'volume_24h']]
    tickers = pd.DataFrame(client.get_ticker())
    tickers['priceChangePercent'] = pd.to_numeric(tickers['priceChangePercent'])
    tickerList = pd.DataFrame()
    tickerList['symbol'] = tickers['symbol']
    tickerList['change_24h'] = tickers['priceChangePercent']
    marketList = pd.merge(marketList, tickerList, on='symbol')
    return marketList

def market_classify(client):
    marketList = pd.DataFrame(client.get_products()['data'])
    btcMarketList = marketList[marketList['quoteAsset']=='BTC']
    usdtMarketList = marketList[marketList['quoteAsset']=='USDT']
    tmp = btcMarketList.merge(usdtMarketList, on="baseAsset", how="left", indicator=True)
    btcOnlyMarketList = list(tmp[tmp["_merge"] == "left_only"].drop(columns=["_merge"])['symbol_x'])
    tmp = usdtMarketList.merge(btcMarketList, on="baseAsset", how="left", indicator=True)
    usdtOnlyMarketList = list(tmp[tmp["_merge"] == "left_only"].drop(columns=["_merge"])['symbol_x'])
    return btcOnlyMarketList, usdtOnlyMarketList

def get_trades(client, market, timeDuration, timeFrame):
    klines = client.get_historical_klines(symbol=market, 
                                          interval=timeFrame, 
                                          start_str=timeDuration)
    n_transactions = sum([item[8] for item in klines])
    toId = client.get_historical_trades(symbol=market, limit=1)[0]['id']
    listId = np.arange(toId-n_transactions+1, toId-10,500)
    trades = []
    for fromId in listId:
        trades = trades+client.get_historical_trades(symbol=market, 
                                                     fromId=str(fromId))
    trades = pd.DataFrame(trades)
    trades['price'] = pd.to_numeric(trades['price'])
    trades['qty'] = pd.to_numeric(trades['qty'])
    trades['time'] = pd.to_datetime(trades['time'], unit='ms')
    return trades

def get_candles(client, market, timeFrame, timeDuration):
    klines = client.get_historical_klines(symbol=market, 
                                          interval=timeFrame, 
                                          start_str=timeDuration)
    klines = pd.DataFrame(klines)    
    candles = pd.DataFrame()  
    candles['open_time'] = klines[0]
    candles['close_time'] = klines[6]
    candles['n_trades'] = klines[8]
    candles['open'] = pd.to_numeric(klines[1])
    candles['high'] = pd.to_numeric(klines[2])
    candles['low'] = pd.to_numeric(klines[3])
    candles['close'] = pd.to_numeric(klines[4])
    candles['assetVolume'] = pd.to_numeric(klines[5])
    candles['buyAssetVolume'] = pd.to_numeric(klines[9])
    candles['sellAssetVolume'] = candles['assetVolume']-candles['buyAssetVolume']
    candles['quoteVolume'] = pd.to_numeric(klines[7])
    candles['buyQuoteVolume'] = pd.to_numeric(klines[10])
    candles['sellQuoteVolume'] = candles['quoteVolume']-candles['buyQuoteVolume']
    candles['spread'] = candles['high']-candles['low']
    return candles

def get_funding_rate(client, market):
    fundingRate = client.futures_funding_rate(symbol=market)
    fundingRate = pd.DataFrame(fundingRate)[['fundingTime', 'fundingRate']] 
    fundingRate['fundingRate'] = pd.to_numeric(fundingRate['fundingRate'])
    fundingRate['fundingTime'] = pd.to_datetime(fundingRate['fundingTime'], unit='ms')
    return fundingRate




     