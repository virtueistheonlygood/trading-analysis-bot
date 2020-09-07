from binance_trading_bot import utilities, visual
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import rcParams
plt.style.use('classic')
rcParams['figure.figsize'] = 5, 15
from matplotlib.ticker import FormatStrFormatter
import matplotlib.patches as mpatches
from itertools import groupby
from operator import itemgetter

def altcoin_scan(client):
    marketList = utilities.get_market_list(client)
    TIME_FRAME = '4h'
    TIME_FRAME_DURATION = '30 days ago UTC'
    for index in marketList.index:
        market = marketList.at[index, 'symbol']
        candles = utilities.get_candles(client, market, TIME_FRAME, TIME_FRAME_DURATION)
        candles['middle'] = .5*(candles['open']+candles['close'])
        bottomIndex = candles['middle'].idxmin()
        bottom = candles.at[bottomIndex, 'middle']
        bottomCandles = candles[candles['low']<=bottom]
        bottomIndices =[]
        for k,g in groupby(enumerate(bottomCandles.index),lambda x:x[0]-x[1]):
            group = (map(itemgetter(1),g))
            group = list(map(int,group))
            bottomIndices.append((group[0],group[-1]))
        marketList.at[index, 'n_bottom'] = len(bottomIndices)
        marketList.at[index, 'bottom'] = bottom
        marketList.at[index, 'price'] = candles.at[candles.index[-1], 'close']
    marketList['diff'] = (marketList['price']-marketList['bottom'])/marketList['bottom']*100
    marketList = marketList.sort_values('diff', ascending=True)
    marketList = marketList.sort_values('n_bottom', ascending=False)
    
    marketListBTC, marketListUSDT = utilities.market_classify(client)
    marketListBTC = marketList[marketList['symbol'].isin(marketListBTC)]
    marketListBTC = marketListBTC.set_index('symbol')

    for i in marketList.index:
        try:
            if marketList['symbol'].at[i][-4:]!='USDT':
                marketList = marketList.drop(i)
        except Exception:
            pass
    marketList = marketList.set_index('symbol')
    
    try:
        marketListBTC.to_csv('data/market_list_btc.csv')
        marketList.to_csv('data/market_list_usdt.csv')
    except Exception:
        pass
    
    return marketListBTC, marketList
    
def market_change(client):
    marketList = pd.DataFrame(client.get_products()['data'])
    parentMarketList = list(set(marketList['parentMarket'].tolist()))
    msg = '*Positive versus negative pairs*'
    for parentMarket in parentMarketList:
        baseAssetList = list(set(marketList[marketList['parentMarket']==parentMarket]['quoteAsset']))
        positiveCount = 0
        negativeCount = 0
        for baseAsset in baseAssetList:
            marketList_ = utilities.get_market_list(client, baseAsset)
            positiveCount = positiveCount+len(marketList_[marketList_['change_24h']>=0.])
            negativeCount = negativeCount+len(marketList_[marketList_['change_24h']<0.])
        msg = msg+'\n'+parentMarket+': '+str(positiveCount)+' (+) '+str(negativeCount)+' (-)'
    return msg

def market_movement(client, timeInterval):
    
    btcOnlyMarketList, usdtOnlyMarketList = utilities.market_classify(client)
    
    marketList = utilities.get_market_list(client, 'BTC')
    exchangeVolume = pd.DataFrame()
    totalVolume = pd.DataFrame()
    buyVolume = pd.DataFrame()
    sellVolume = pd.DataFrame()
    for market in btcOnlyMarketList:
        try:
            candles = utilities.get_candles(client, market, timeFrame='1d', timeDuration=str(timeInterval)+' days ago UTC')
            totalVolume[market] = candles['quoteVolume']
            totalVolume = totalVolume.fillna(0.)
            buyVolume[market] = candles['buyQuoteVolume']
            buyVolume = buyVolume.fillna(0.)
            sellVolume[market] = candles['sellQuoteVolume']
            sellVolume = sellVolume.fillna(0.)
        except Exception:
            pass
    exchangeVolume['volume'] = totalVolume.iloc[:, :].sum(axis=1)
    exchangeVolume['buy-volume'] = buyVolume.iloc[:, :].sum(axis=1)
    exchangeVolume['sell-volume'] = sellVolume.iloc[:, :].sum(axis=1)
    
    f, axes = plt.subplots(2, 1, gridspec_kw={'height_ratios':[1, 1]})
    f.set_size_inches(20,15)
    
    ax = axes[0]
    candles = utilities.get_candles(client, market='BTCUSDT', timeFrame='1d', timeDuration=str(timeInterval)+' days ago UTC')
    visual.candlestick2_ohlc(ax, 
                             candles['open'],
                             candles['high'],
                             candles['low'],
                             candles['close'],
                             width=0.6, alpha=1)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(.5, timeInterval)
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.set_title('Binance Exchange Daily Movement Statistics over '+str(timeInterval)+' day period', fontsize=30, y=1.03, loc='center')
    ax.set_ylabel("Bitcoin Price", fontsize=20)
    
    ax = axes[1] 
    visual.candlestick2_ohlc(ax,
                             0*exchangeVolume['volume'],
                             exchangeVolume['volume'],
                             0*exchangeVolume['volume'],
                             exchangeVolume['volume'],
                             width=0.6, alpha=.35)
    visual.candlestick2_ohlc(ax,
                             0*exchangeVolume['buy-volume'],
                             exchangeVolume['buy-volume'],
                             0*exchangeVolume['buy-volume'],
                             exchangeVolume['buy-volume'],
                             width=0.28, alpha=1, shift=-0.15)
    visual.candlestick2_ohlc(ax,
                             exchangeVolume['sell-volume'],
                             exchangeVolume['sell-volume'],
                             0*exchangeVolume['sell-volume'],
                             0*exchangeVolume['sell-volume'],
                             width=0.28, alpha=1, shift=+0.15)
    ax.plot(exchangeVolume['volume'].rolling(window=20).mean(), linewidth=2, color='gray', linestyle='-')
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(.5, timeInterval)
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.set_ylabel("Altcoin Total Volume ("+str(len(btcOnlyMarketList))+"/"+str(len(marketList))+" pairs)", fontsize=20)
    
    patchList = [mpatches.Patch(color='gray', label='volume'),
                 mpatches.Patch(color='black', label='buy-volume'),
                 mpatches.Patch(color='red', label='sell-volume')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=1, framealpha=0.5)
    
    f.tight_layout()
    plt.savefig('img/market.png', bbox_inches='tight')
    
