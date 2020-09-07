from binance_trading_bot import utilities, visual
import pandas as pd
import requests, json, re
from six.moves import urllib
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
plt.style.use('classic')
from matplotlib.ticker import FormatStrFormatter
import matplotlib.patches as mpatches
import time
from datetime import datetime 

def orderbook_analysis(client, market):
    orderBook = client.get_order_book(symbol=market, limit=5000)
    orderBook = pd.DataFrame(orderBook['bids']+orderBook['asks'])
    orderBook[0] = orderBook[0].apply(pd.to_numeric, errors = 'coerce')
    orderBook[1] = orderBook[1].apply(pd.to_numeric, errors = 'coerce')
    orderBook.columns = ['price', 'qty']
    orderBook = orderBook.sort_values('qty', axis=0, ascending=False)[:20].reset_index(drop=True)
    pd.options.display.float_format = '{:,.0f}'.format
    msg = orderBook.to_string()
    return msg

def asset_analysis(client, asset):
    marketList = pd.DataFrame(client.get_products()['data'])
    marketList = marketList[marketList['baseAsset']==asset]
    marketList['volume'] = pd.to_numeric(marketList['volume'])
    marketList = marketList.sort_values('volume', ascending=False)
    msg = ''
    for index in marketList.index:
        try:
            market = marketList.at[index, 'symbol']
            candles = utilities.get_candles(client, 
                                            market, 
                                            timeFrame='5m', 
                                            timeDuration='30 minutes ago utc')
            result = pd.DataFrame(columns=['Duration', ': Buy ', ' Sell '])
            for i in [2, 1, 0]:
                result.loc[2-i] = [str(5*(i+2**i))+' mins', 
                          "{0:,.2f}".format(candles['buyQuoteVolume'].iloc[-max(3*i, 1):].sum()),
                          "{0:,.2f}".format(candles['sellQuoteVolume'].iloc[-max(3*i, 1):].sum())]
            msg = msg+'#'+market+' '\
            "{0:,.2f}".format(float(marketList.at[index, 'volume']))+' ('+\
             "{0:,.2f}".format(float(marketList.at[index, 'volume']/sum(marketList['volume'])*100))+'%)'+\
            '\nP: '+"{0:,.8f}".format(float(marketList.at[index, 'close']))+\
            ' V: '+"{0:,.2f}".format(float(marketList.at[index, 'tradedMoney']))+\
            ' VWAP: '+client.get_ticker(symbol=market)['weightedAvgPrice']
            for i in range(len(result)):
                msg = msg+'\n'+result[result.columns[0]].loc[i]+\
                result.columns[1]+'*'+result[result.columns[1]].loc[i]+'*'+\
                result.columns[2]+'*'+result[result.columns[2]].loc[i]+'*'
            msg = msg+'\n'
        except Exception:
            pass
    return msg

def asset_info(client, asset):
    marketList = pd.DataFrame(client.get_products()['data'])
    base = marketList[marketList['baseAsset']==asset]['marketName'].iloc[0]
    marketURL = 'https://www.binance.com/en/trade/'+asset+'_'+base
    marketPage = requests.get(marketURL)
    marketHTML = marketPage.text
    marketSoup = BeautifulSoup(marketHTML, features="html.parser")
    infoURL = marketSoup.find("div", attrs={"class":"sc-62mpio-0 hGTHme"}).find("a")['href']
    infoPage = requests.get(infoURL)
    infoHTML = infoPage.text
    infoSoup = BeautifulSoup(infoHTML, features="html.parser")
    table = infoSoup.find("table", attrs={"class":"s1qusdff-2 iGhOhQ"})
    headings = [th.get_text() for th in table.find_all("th")]
    contents = [th.get_text() for th in table.find_all("td")]
    headings.append('Market Cap')
    headings.append('Current Price')
    headings.append('Social Media')
    contents.append(infoSoup.find("div", attrs={"class":"ix71fe-6 gKwfCV"}).find("li").find("div").text)
    contents.append(infoSoup.find("div", attrs={"class":"ix71fe-2 bpheZt"}).find("div").text)
    try:
        elements = infoSoup.findAll("a", attrs={"class":"s1f3siel-4 BppNm"})
        communityURL = ''
        for element in elements:
            communityURL = communityURL+'\n'+'['+element['href']+']('+element['href']+')'
    except Exception:
        communityURL = ''
    contents.append(communityURL)
    headings.append('Explorers')
    try:
        try:
            elements = infoSoup.findAll("div", attrs={"class":"infoline"})[2].findAll("a", attrs={"class":"s1re75us-3 hBLTSO"})
            explorerURL = ''
            for element in elements:
                explorerURL = explorerURL+'\n'+'['+element['href']+']('+element['href']+')'
        except Exception:
            elements = infoSoup.findAll("div", attrs={"class":"infoline"})[1].findAll("a", attrs={"class":"s1re75us-3 hBLTSO"})
            explorerURL = ''
            for element in elements:
                explorerURL = explorerURL+'\n'+'['+element['href']+']('+element['href']+')'
    except Exception:
        explorerURL = ''
    contents.append(explorerURL)
    data = pd.DataFrame([contents], columns=headings)
    data = data[['Type', 'Consensus Protocol', 'Cryptographic Algorithm',
                 'Website', 'Social Media', 'Explorers',
                 'Market Cap', 'Current Price', 
                 'Issue Price', 'Issue Date', 
                 'Max Supply', 'Total Supply', 'Circulating Supply']]
    msg = '#'+asset
    for param in data.columns:
        msg = msg+'\n'+param+': '+data.loc[0, param]
    return msg

def exchange_flows(twitterApi):
    
    userName = 'thetokenanalyst'
    userTweets = twitterApi.user_timeline(screen_name = userName, 
                                          count=200, 
                                          include_rts = False, 
                                          tweet_mode = 'extended')
    
    searchString = '24H BTC'
    for status in userTweets:
        if searchString in status.full_text:
            break
    lines = status.full_text.splitlines()
    lines = [line[1:].capitalize().replace("m in", "M in").replace("m out", "M out") for line in lines if line[0:1]=='#']
    msg = '*Daily BTC exchange flows*'
    for line in lines:
        msg = msg+'\n#'+line
        
    searchString = '24H ETH'
    for status in userTweets:
        if searchString in status.full_text:
            break
    lines = status.full_text.splitlines()
    lines = [line[1:].capitalize().replace("m in", "M in").replace("m out", "M out") for line in lines if line[0:1]=='#']
    msg = msg+'\n*Daily ETH exchange flows*'
    for line in lines:
        msg = msg+'\n#'+line
        
    searchString = 'Weekly BTC'
    for status in userTweets:
        if searchString in status.full_text:
            break
    lines = status.full_text.splitlines()
    lines = [line[2:] for line in lines if '$' in line]    
    msg = msg+'\n*Weekly BTC exchange flows*'
    for line in lines:
        msg = msg+'\n'+line
        
    searchString = 'Weekly ETH'
    for status in userTweets:
        if searchString in status.full_text:
            break
    lines = status.full_text.splitlines()
    lines = [line[2:] for line in lines if '$' in line]    
    msg = msg+'\n*Weekly ETH exchange flows*'
    for line in lines:
        msg = msg+'\n'+line
        
    searchString = 'Weekly Stablecoin'
    for status in userTweets:
        if searchString in status.full_text:
            break
    lines = status.full_text.splitlines()
    lines = [line[2:] for line in lines if '$' in line]    
    msg = msg+'\n*Weekly Stablecoin exchange flows*'
    for line in lines:
        msg = msg+'\n'+line
        
    return msg

def exchange_flows_visual(twitterApi):
    userTweets = twitterApi.user_timeline(screen_name = 'thetokenanalyst', 
                                          count=200, 
                                          include_rts = False, 
                                          tweet_mode = 'extended')
    dates = []
    bitstamp_inflows = []
    bitstamp_outflows = []
    binance_inflows = []
    binance_outflows = []
    for status in userTweets:
        if '24H BTC' in status.full_text:
            lines = status.full_text.splitlines()
            for line in lines:
                if 'binance' in line:
                    dates.append(status.created_at.date())
                    flows = re.findall(r'\$\d+M', line)
                    binance_inflows.append(int(flows[0][1:-1]))
                    binance_outflows.append(int(flows[1][1:-1]))
                if 'bitstamp' in line:
                    flows = re.findall(r'\$\d+M', line)
                    bitstamp_inflows.append(int(flows[0][1:-1]))
                    bitstamp_outflows.append(int(flows[1][1:-1]))
                    
    data = pd.DataFrame(
        {'date': list(reversed(dates)),
         'binance-inflow': list(reversed(binance_inflows)),
         'binance-outflow': list(reversed(binance_outflows)),
         'bitstamp-inflow': list(reversed(bitstamp_inflows)),
         'bitstamp-outflow': list(reversed(bitstamp_outflows))
        })
    
    f, axes = plt.subplots(2, 1, gridspec_kw={'height_ratios':[1, 1]})
    f.set_size_inches(15,8)
    
    ax = axes[0]
    visual.candlestick2_ohlc(ax,
                             0*data['binance-inflow'],
                             data['binance-inflow'],
                             0*data['binance-inflow'],
                             data['binance-inflow'],
                             width=0.28, alpha=1, shift=-0.15)
    visual.candlestick2_ohlc(ax,
                             data['binance-outflow'],
                             data['binance-outflow'],
                             0*data['binance-outflow'],
                             0*data['binance-outflow'],
                             width=0.28, alpha=1, shift=+0.15)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(-.5, len(data))
    ax.get_yaxis().set_label_coords(-0.05,0.5)  
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Binance",fontsize=20)
    ax.set_title("Bitcoin 24h Exchange On-chain Flows", fontsize=30, y=1.03, loc='center')
    
    patchList = [mpatches.Patch(color='black', label='Inflows'),
                 mpatches.Patch(color='red', label='Outflows')]
    ax.legend(handles=patchList, loc='best', prop={'size': 20}, ncol=len(patchList), framealpha=0.5)
    
    ax = axes[1]
    visual.candlestick2_ohlc(ax,
                             0*data['bitstamp-inflow'],
                             data['bitstamp-inflow'],
                             0*data['bitstamp-inflow'],
                             data['bitstamp-inflow'],
                             width=0.28, alpha=1, shift=-0.15)
    visual.candlestick2_ohlc(ax,
                             data['bitstamp-outflow'],
                             data['bitstamp-outflow'],
                             0*data['bitstamp-outflow'],
                             0*data['bitstamp-outflow'],
                             width=0.28, alpha=1, shift=+0.15)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.set_xlim(-.5, len(data))
    ax.get_yaxis().set_label_coords(-0.05,0.5)  
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Bitstamp",fontsize=20)
    
    f.tight_layout()
    plt.savefig('img/bitcoin_exchange_flows.png', bbox_inches='tight')
    
def transaction_activities(twitterApi, keywords):
    
    n_activities = 15
    userName = 'whale_alert'
    userTweets = twitterApi.user_timeline(screen_name = userName, 
                                          count=1000, 
                                          include_rts = False, 
                                          tweet_mode = 'extended')
    
    msg = '*Transaction activities*'
    count = 0
    for status in userTweets:
        check = 0
        for keyword in keywords:
            if keyword in status.full_text:
                check = check+1
        if check==len(keywords):
            msg = msg+'\n'+\
            str(status.created_at)+\
            ': '+status.full_text.splitlines()[0]
            count = count+1
            if count>n_activities:
                break
    
    return msg

def liquidation_activities(twitterApi, keywords):
    
    n_activities = 15
    userName = 'BXRekt'
    userTweets = twitterApi.user_timeline(screen_name = userName, 
                                          count=1000, 
                                          include_rts = False, 
                                          tweet_mode = 'extended')
    
    msg = '*Liquidation activities*'
    count = 0
    for status in userTweets:
        check = 0
        for keyword in keywords:
            if keyword in status.full_text:
                check = check+1
        if check==len(keywords):
            msg = msg+'\n'+\
            str(status.created_at)+\
            ': '+status.full_text.splitlines()[0]
            count = count+1
            if count>n_activities:
                break
            
    keywords = ['Liquidated', 'XBTUSD']   
    qtyList = []
    priceList = []
    timeList = []
    typeList = []
    for status in userTweets:
        check = 0
        for keyword in keywords:
            if keyword in status.full_text:
                check = check+1
        if check==len(keywords):
            temp = []
            for t in status.full_text.splitlines()[0].replace(',', '').split():
                try:
                    temp.append(float(t))
                except ValueError:
                    pass
            qty = temp[:len(temp)//2]
            price = temp[len(temp)//2:]
            for i in range(len(qty)):
                timeList.append(int(round(status.created_at.timestamp())))
                qtyList.append(qty[i])
                priceList.append(price[i])
                if 'long' in status.full_text:
                    typeList.append(1)
                else:
                    typeList.append(-1)
    qtyList = [2e3*float(i)/max(qtyList) for i in qtyList]
    
    f,ax = plt.subplots(1, 1, gridspec_kw={'height_ratios':[1]})
    f.set_size_inches(15, 7)
    ax.scatter([timeList[i] for i in range(len(timeList)) if typeList[i]==1], 
                [priceList[i] for i in range(len(timeList)) if typeList[i]==1], 
                s=[qtyList[i] for i in range(len(timeList)) if typeList[i]==1], 
                c='g', marker='o', alpha=.5)
    ax.scatter([timeList[i] for i in range(len(timeList)) if typeList[i]==-1], 
                [priceList[i] for i in range(len(timeList)) if typeList[i]==-1], 
                s=[qtyList[i] for i in range(len(timeList)) if typeList[i]==-1], 
                c='r', marker='o', alpha=.5)
    ax.yaxis.grid(True)
    for tic in ax.xaxis.get_major_ticks():
        tic.tick1On = tic.tick2On = False
        tic.label1On = tic.label2On = False
    ax.set_xticks([])
    ax.get_yaxis().set_label_coords(-0.075,0.5) 
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    ax.get_xaxis().set_label_coords(0.5, -0.025) 
    ax.set_ylabel("Price", fontsize=20)
    ax.set_title('BitMEX XBTUSD Liquidations', fontsize=30, y=1.03, loc='left')
    f.tight_layout()
    plt.savefig('img/bitmex_liquidations.png', bbox_inches='tight')
    
    return msg

def newsflow():
    url = "https://data.messari.io/api/v1/news"
    data = json.loads(urllib.request.urlopen(url).read().decode('utf-8'))['data']
    msg = '*Newsflow*'
    for item in data[:24]:
        try:
            msg = msg+'\n- '+item['title']
            if len(item['tags'])>0:
                for tag in item['tags']:
                    msg = msg+' #'+tag.upper()
        except Exception:
            pass
    msg = msg+'\nSource: https://messari.io'
    return msg



