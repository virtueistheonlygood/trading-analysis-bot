from binance_trading_bot import utilities, visual, indicator
import matplotlib.pyplot as plt
plt.style.use('classic')
from matplotlib.ticker import FormatStrFormatter
import matplotlib.patches as mpatches
import math

def volume_spread_analysis(client, market, 
                           NUM_PRICE_STEP, TIME_FRAME_STEP, TIME_FRAME, TIME_FRAME_DURATION):
    
    nDigit = abs(int(math.log10(float(client.get_symbol_info(market)['filters'][0]['tickSize']))))
    candles = utilities.get_candles(client, market, TIME_FRAME, TIME_FRAME_DURATION)
    
    VRVP = indicator.volume_profile(client, market, NUM_PRICE_STEP, TIME_FRAME_STEP, TIME_FRAME_DURATION)
    BBANDS = indicator.bbands(candles)
    VSTOP = indicator.volatility_stop(candles, 20, 2)
    RSI = indicator.rsi(candles, 14)
    SMA = indicator.sma(candles)
     
    # Visualization
    VSTOP_COLOR = 'indigo'
    SMA_COLOR = 'black'
    BBANDS_COLOR = 'green'
    VOLUME_COLOR = 'gray'
    BUY_COLOR = 'black'
    SELL_COLOR = 'red'
    VOLATILITY_COLOR = 'black'
    RSI_COLOR = 'black'
    
    f,axes = plt.subplots(4, 1, gridspec_kw={'height_ratios':[3, 1, 1, 1]})
    f.set_size_inches(20,20)
     
    ax = axes[0]
    axt = ax.twiny()
    axt.barh(VRVP['price'],
             VRVP['buy_volume'],
             color='gray',
             edgecolor='w',
             height=VRVP['price'][1]-VRVP['price'][0],
             align='center',
             alpha=0.25)
    axt.barh(VRVP['price'],
             VRVP['buy_volume']+VRVP['sell_volume'],
             color='gray',
             edgecolor='w',
             height=VRVP['price'][1]-VRVP['price'][0],
             align='center',
             alpha=0.25)
    axt.set_xticks([])
    for tic in axt.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    
    visual.candlestick2_ohlc(ax, 
                             candles['open'],
                             candles['high'],
                             candles['low'],
                             candles['close'],
                             width=0.6, alpha=1)
    ax.plot(VSTOP['support'], linewidth=2, color=VSTOP_COLOR, linestyle='-')
    ax.plot(VSTOP['resistance'], linewidth=2, color=VSTOP_COLOR, linestyle='-')
    ax.plot(BBANDS['middle_band'], linewidth=1, color=BBANDS_COLOR, linestyle='-')
    ax.plot(BBANDS['upper_band'], linewidth=1, color=BBANDS_COLOR, linestyle='-')
    ax.plot(BBANDS['lower_band'], linewidth=1, color=BBANDS_COLOR, linestyle='-')
    ax.plot(SMA, linewidth=1, color=SMA_COLOR, linestyle='--')
    
    if market=='BTCUSDT':
        pivotList = []
        for i in range(len(VSTOP)):
            if math.isnan(VSTOP['support'].iat[i]):
                if not math.isnan(VSTOP['support'].iat[i-1]):
                    pivotList.append(VSTOP['support'].iat[i-1])
            if math.isnan(VSTOP['resistance'].iat[i]):
                if not math.isnan(VSTOP['resistance'].iat[i-1]):
                    pivotList.append(VSTOP['resistance'].iat[i-1])
        pivotList = sorted(pivotList)
        for pivot in pivotList:
            ax.text(len(candles)+.5, pivot, str(int(pivot)))
        
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_yticks(VRVP['price_min'].append(VRVP['price_max'].tail(1)))
    ax.set_xlim(-.5, len(candles))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.'+str(nDigit)+'f'))
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.set_ylabel("Price",fontsize=20)
    ax.set_title(market+' '+TIME_FRAME.upper(), fontsize=30, y=1.03, loc='left')
    
    patchList = [mpatches.Patch(color=VOLUME_COLOR, label='market-profile'),
                 mpatches.Patch(color=VSTOP_COLOR, label='volatility-stop'),
                 mpatches.Patch(color=BBANDS_COLOR, label='bollinger-bands'),
                 mpatches.Patch(color=SMA_COLOR, label='moving-average')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=len(patchList),framealpha=0.5)
    
    ax = axes[1]
    visual.candlestick2_ohlc(ax,
                             0*candles['assetVolume'],
                             candles['assetVolume'],
                             0*candles['assetVolume'],
                             candles['assetVolume'],
                             width=0.6, alpha=.35)
    visual.candlestick2_ohlc(ax,
                             0*candles['buyAssetVolume'],
                             candles['buyAssetVolume'],
                             0*candles['buyAssetVolume'],
                             candles['buyAssetVolume'],
                             width=0.28, alpha=1, shift=-0.15)
    visual.candlestick2_ohlc(ax,
                             candles['sellAssetVolume'],
                             candles['sellAssetVolume'],
                             0*candles['sellAssetVolume'],
                             0*candles['sellAssetVolume'],
                             width=0.28, alpha=1, shift=+0.15)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(-.5, len(candles))
    ax.get_yaxis().set_label_coords(-0.075,0.5)  
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Volume",fontsize=20)
    
    patchList = [mpatches.Patch(color=VOLUME_COLOR, label='volume'),
                 mpatches.Patch(color=BUY_COLOR, label='buy-volume'),
                 mpatches.Patch(color=SELL_COLOR, label='sell-volume')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=len(patchList), framealpha=0.5)
    
    ax = axes[2]
    visual.candlestick2_ohlc(ax,
                             0*candles['spread'],
                             candles['spread'],
                             0*candles['spread'],
                             candles['spread'],
                             width=0.6, colorup=VOLATILITY_COLOR, alpha=.35)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(-.5, len(candles))
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.'+str(nDigit)+'f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Volatility",fontsize=20)
    
    patchList = [mpatches.Patch(color=VOLATILITY_COLOR, label='average-true-range'),
                 mpatches.Patch(color=BBANDS_COLOR, label='standard-deviation')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=len(patchList), framealpha=0.5)
    
    axt = ax.twinx()
    axt.plot(BBANDS['std'], linewidth=2, color=BBANDS_COLOR, linestyle='-')
    for tic in axt.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    axt.set_xticks([])
    axt.set_yticks([])
    axt.set_xlim(-.5, len(candles))
    
    axt = ax.twinx()
    axt.plot(VSTOP['ATR'], linewidth=2, color=VOLATILITY_COLOR, linestyle='-')
    for tic in axt.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    axt.set_xticks([])
    axt.set_xlim(-.5, len(candles))
    
    ax = axes[3]
    ax.plot(RSI, linewidth=2, color=RSI_COLOR, linestyle='-')
    ax.axhline(y=50, color=RSI_COLOR, linestyle='--')
    ax.axhspan(ymin=20, ymax=80, color=RSI_COLOR, alpha=0.1)
    ax.axhspan(ymin=30, ymax=70, color=RSI_COLOR, alpha=0.1)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(-.5, len(candles))
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.'+str(nDigit)+'f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Momentum",fontsize=20)
    
    patchList = [mpatches.Patch(color=RSI_COLOR, label='relative-strength')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=len(patchList), framealpha=0.5)
      
    f.tight_layout()
    plt.savefig('img/'+market+'_'+TIME_FRAME.upper()+'.png', bbox_inches='tight')