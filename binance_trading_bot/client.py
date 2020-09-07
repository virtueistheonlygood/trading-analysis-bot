# coding=utf-8

import hashlib
import hmac
import requests
import time
from operator import itemgetter
from .helpers import date_to_milliseconds, interval_to_milliseconds
from .exceptions import BinanceAPIException, BinanceRequestException, BinanceWithdrawException


class Client(object):

    API_URL = 'https://api.binance.com/api'
    WITHDRAW_API_URL = 'https://api.binance.com/wapi'
    MARGIN_API_URL = 'https://api.binance.com/sapi'
    FUTURES_API_URL = 'https://fapi.binance.com/fapi'
    WEBSITE_URL = 'https://www.binance.com'
    PUBLIC_API_VERSION = 'v1'
    PRIVATE_API_VERSION = 'v3'
    WITHDRAW_API_VERSION = 'v3'
    MARGIN_API_VERSION = 'v1'
    FUTURES_API_VERSION = 'v1'

    SYMBOL_TYPE_SPOT = 'SPOT'

    ORDER_STATUS_NEW = 'NEW'
    ORDER_STATUS_PARTIALLY_FILLED = 'PARTIALLY_FILLED'
    ORDER_STATUS_FILLED = 'FILLED'
    ORDER_STATUS_CANCELED = 'CANCELED'
    ORDER_STATUS_PENDING_CANCEL = 'PENDING_CANCEL'
    ORDER_STATUS_REJECTED = 'REJECTED'
    ORDER_STATUS_EXPIRED = 'EXPIRED'

    KLINE_INTERVAL_1MINUTE = '1m'
    KLINE_INTERVAL_3MINUTE = '3m'
    KLINE_INTERVAL_5MINUTE = '5m'
    KLINE_INTERVAL_15MINUTE = '15m'
    KLINE_INTERVAL_30MINUTE = '30m'
    KLINE_INTERVAL_1HOUR = '1h'
    KLINE_INTERVAL_2HOUR = '2h'
    KLINE_INTERVAL_4HOUR = '4h'
    KLINE_INTERVAL_6HOUR = '6h'
    KLINE_INTERVAL_8HOUR = '8h'
    KLINE_INTERVAL_12HOUR = '12h'
    KLINE_INTERVAL_1DAY = '1d'
    KLINE_INTERVAL_3DAY = '3d'
    KLINE_INTERVAL_1WEEK = '1w'
    KLINE_INTERVAL_1MONTH = '1M'

    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'

    ORDER_TYPE_LIMIT = 'LIMIT'
    ORDER_TYPE_MARKET = 'MARKET'
    ORDER_TYPE_STOP_LOSS = 'STOP_LOSS'
    ORDER_TYPE_STOP_LOSS_LIMIT = 'STOP_LOSS_LIMIT'
    ORDER_TYPE_TAKE_PROFIT = 'TAKE_PROFIT'
    ORDER_TYPE_TAKE_PROFIT_LIMIT = 'TAKE_PROFIT_LIMIT'
    ORDER_TYPE_LIMIT_MAKER = 'LIMIT_MAKER'

    TIME_IN_FORCE_GTC = 'GTC'  # Good till cancelled
    TIME_IN_FORCE_IOC = 'IOC'  # Immediate or cancel
    TIME_IN_FORCE_FOK = 'FOK'  # Fill or kill

    ORDER_RESP_TYPE_ACK = 'ACK'
    ORDER_RESP_TYPE_RESULT = 'RESULT'
    ORDER_RESP_TYPE_FULL = 'FULL'

    # For accessing the data returned by Client.aggregate_trades().
    AGG_ID = 'a'
    AGG_PRICE = 'p'
    AGG_QUANTITY = 'q'
    AGG_FIRST_TRADE_ID = 'f'
    AGG_LAST_TRADE_ID = 'l'
    AGG_TIME = 'T'
    AGG_BUYER_MAKES = 'm'
    AGG_BEST_MATCH = 'M'

    def __init__(self, api_key, api_secret, requests_params=None):
        self.API_KEY = api_key
        self.API_SECRET = api_secret
        self.session = self._init_session()
        self._requests_params = requests_params

        # init DNS and SSL cert
        self.ping()

    def _init_session(self):
        session = requests.session()
        session.headers.update({'Accept': 'application/json',
                                'User-Agent': 'binance/python',
                                'X-MBX-APIKEY': self.API_KEY})
        return session

    def _create_api_uri(self, path, signed=True, version=PUBLIC_API_VERSION):
        v = self.PRIVATE_API_VERSION if signed else version
        return self.API_URL + '/' + v + '/' + path

    def _create_withdraw_api_uri(self, path):
        return self.WITHDRAW_API_URL + '/' + self.WITHDRAW_API_VERSION + '/' + path

    def _create_margin_api_uri(self, path):
        return self.MARGIN_API_URL + '/' + self.MARGIN_API_VERSION + '/' + path
    
    def _create_futures_api_uri(self, path):
        return self.FUTURES_API_URL + '/' + self.FUTURES_API_VERSION + '/' + path

    def _create_website_uri(self, path):
        return self.WEBSITE_URL + '/' + path

    def _generate_signature(self, data):
        ordered_data = self._order_params(data)
        query_string = '&'.join(["{}={}".format(d[0], d[1]) for d in ordered_data])
        m = hmac.new(self.API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256)
        return m.hexdigest()

    def _order_params(self, data):
        has_signature = False
        params = []
        for key, value in data.items():
            if key == 'signature':
                has_signature = True
            else:
                params.append((key, value))
        # sort parameters by key
        params.sort(key=itemgetter(0))
        if has_signature:
            params.append(('signature', data['signature']))
        return params

    def _request(self, method, uri, signed, force_params=False, **kwargs):

        # set default requests timeout
        kwargs['timeout'] = 10

        # add our global requests params
        if self._requests_params:
            kwargs.update(self._requests_params)

        data = kwargs.get('data', None)
        if data and isinstance(data, dict):
            kwargs['data'] = data

            # find any requests params passed and apply them
            if 'requests_params' in kwargs['data']:
                # merge requests params into kwargs
                kwargs.update(kwargs['data']['requests_params'])
                del(kwargs['data']['requests_params'])

        if signed:
            # generate signature
            kwargs['data']['timestamp'] = int(time.time() * 1000)
            kwargs['data']['signature'] = self._generate_signature(kwargs['data'])

        # sort get and post params to match signature order
        if data:
            # sort post params
            kwargs['data'] = self._order_params(kwargs['data'])

        # if get request assign data array to params value for requests lib
        if data and (method == 'get' or force_params):
            kwargs['params'] = kwargs['data']
            del(kwargs['data'])

        response = getattr(self.session, method)(uri, **kwargs)
        return self._handle_response(response)

    def _request_api(self, method, path, signed=False, version=PUBLIC_API_VERSION, **kwargs):
        uri = self._create_api_uri(path, signed, version)

        return self._request(method, uri, signed, **kwargs)

    def _request_withdraw_api(self, method, path, signed=False, **kwargs):
        uri = self._create_withdraw_api_uri(path)

        return self._request(method, uri, signed, True, **kwargs)

    def _request_margin_api(self, method, path, signed=False, **kwargs):
        uri = self._create_margin_api_uri(path)

        return self._request(method, uri, signed, **kwargs)
    
    def _request_futures_api(self, method, path, signed=False, **kwargs):
        uri = self._create_futures_api_uri(path)

        return self._request(method, uri, signed, **kwargs)

    def _request_website(self, method, path, signed=False, **kwargs):

        uri = self._create_website_uri(path)

        return self._request(method, uri, signed, **kwargs)

    def _handle_response(self, response):
        if not str(response.status_code).startswith('2'):
            raise BinanceAPIException(response)
        try:
            return response.json()
        except ValueError:
            raise BinanceRequestException('Invalid Response: %s' % response.text)

    def _get(self, path, signed=False, version=PUBLIC_API_VERSION, **kwargs):
        return self._request_api('get', path, signed, version, **kwargs)

    def _post(self, path, signed=False, version=PUBLIC_API_VERSION, **kwargs):
        return self._request_api('post', path, signed, version, **kwargs)

    def _put(self, path, signed=False, version=PUBLIC_API_VERSION, **kwargs):
        return self._request_api('put', path, signed, version, **kwargs)

    def _delete(self, path, signed=False, version=PUBLIC_API_VERSION, **kwargs):
        return self._request_api('delete', path, signed, version, **kwargs)

    # Exchange Endpoints

    def get_products(self):
        products = self._request_website('get', 'exchange/public/product')
        return products

    def get_exchange_info(self):
        return self._get('exchangeInfo')

    def get_symbol_info(self, symbol):
        res = self._get('exchangeInfo')

        for item in res['symbols']:
            if item['symbol'] == symbol.upper():
                return item

        return None

    # General Endpoints

    def ping(self):
        return self._get('ping')

    def get_server_time(self):
        return self._get('time')

    # Market Data Endpoints

    def get_all_tickers(self):
        return self._get('ticker/allPrices')

    def get_orderbook_tickers(self):
        return self._get('ticker/allBookTickers')

    def get_order_book(self, **params):
        return self._get('depth', data=params)

    def get_recent_trades(self, **params):
        return self._get('trades', data=params)

    def get_historical_trades(self, **params):
        return self._get('historicalTrades', data=params)

    def get_aggregate_trades(self, **params):
        return self._get('aggTrades', data=params)

    def aggregate_trade_iter(self, symbol, start_str=None, last_id=None):

        if start_str is not None and last_id is not None:
            raise ValueError(
                'start_time and last_id may not be simultaneously specified.')

        # If there's no last_id, get one.
        if last_id is None:
            # Without a last_id, we actually need the first trade.  Normally,
            # we'd get rid of it. See the next loop.
            if start_str is None:
                trades = self.get_aggregate_trades(symbol=symbol, fromId=0)
            else:
                # The difference between startTime and endTime should be less
                # or equal than an hour and the result set should contain at
                # least one trade.
                if type(start_str) == int:
                    start_ts = start_str
                else:
                    start_ts = date_to_milliseconds(start_str)
                # If the resulting set is empty (i.e. no trades in that interval)
                # then we just move forward hour by hour until we find at least one
                # trade or reach present moment
                while True:
                    end_ts = start_ts + (60 * 60 * 1000)
                    trades = self.get_aggregate_trades(
                        symbol=symbol,
                        startTime=start_ts,
                        endTime=end_ts)
                    if len(trades) > 0:
                        break
                    # If we reach present moment and find no trades then there is
                    # nothing to iterate, so we're done
                    if end_ts > int(time.time() * 1000):
                        return
                    start_ts = end_ts
            for t in trades:
                yield t
            last_id = trades[-1][self.AGG_ID]

        while True:
            # There is no need to wait between queries, to avoid hitting the
            # rate limit. We're using blocking IO, and as long as we're the
            # only thread running calls like this, Binance will automatically
            # add the right delay time on their end, forcing us to wait for
            # data. That really simplifies this function's job. Binance is
            # fucking awesome.
            trades = self.get_aggregate_trades(symbol=symbol, fromId=last_id)
            # fromId=n returns a set starting with id n, but we already have
            # that one. So get rid of the first item in the result set.
            trades = trades[1:]
            if len(trades) == 0:
                return
            for t in trades:
                yield t
            last_id = trades[-1][self.AGG_ID]

    def get_klines(self, **params):
        return self._get('klines', data=params)

    def _get_earliest_valid_timestamp(self, symbol, interval):
        kline = self.get_klines(
            symbol=symbol,
            interval=interval,
            limit=1,
            startTime=0,
            endTime=None
        )
        return kline[0][0]

    def get_historical_klines(self, symbol, interval, start_str, end_str=None,
                              limit=500):

        # init our list
        output_data = []

        # setup the max limit
        limit = limit

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # convert our date strings to milliseconds
        if type(start_str) == int:
            start_ts = start_str
        else:
            start_ts = date_to_milliseconds(start_str)

        # establish first available start timestamp
        first_valid_ts = self._get_earliest_valid_timestamp(symbol, interval)
        start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = None
        if end_str:
            if type(end_str) == int:
                end_ts = end_str
            else:
                end_ts = date_to_milliseconds(end_str)

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            temp_data = self.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_ts,
                endTime=end_ts
            )

            # handle the case where exactly the limit amount of data was returned last loop
            if not len(temp_data):
                break

            # append this loops data to our output data
            output_data += temp_data

            # set our start timestamp using the last value in the array
            start_ts = temp_data[-1][0]

            idx += 1
            # check if we received less than the required limit and exit the loop
            if len(temp_data) < limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_ts += timeframe

            # sleep after every 3rd call to be kind to the API
            if idx % 3 == 0:
                time.sleep(1)

        return output_data

    def get_historical_klines_generator(self, symbol, interval, start_str, end_str=None):

        # setup the max limit
        limit = 500

        # convert interval to useful value in seconds
        timeframe = interval_to_milliseconds(interval)

        # convert our date strings to milliseconds
        if type(start_str) == int:
            start_ts = start_str
        else:
            start_ts = date_to_milliseconds(start_str)

        # establish first available start timestamp
        first_valid_ts = self._get_earliest_valid_timestamp(symbol, interval)
        start_ts = max(start_ts, first_valid_ts)

        # if an end time was passed convert it
        end_ts = None
        if end_str:
            if type(end_str) == int:
                end_ts = end_str
            else:
                end_ts = date_to_milliseconds(end_str)

        idx = 0
        while True:
            # fetch the klines from start_ts up to max 500 entries or the end_ts if set
            output_data = self.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_ts,
                endTime=end_ts
            )

            # handle the case where exactly the limit amount of data was returned last loop
            if not len(output_data):
                break

            # yield data
            for o in output_data:
                yield o

            # set our start timestamp using the last value in the array
            start_ts = output_data[-1][0]

            idx += 1
            # check if we received less than the required limit and exit the loop
            if len(output_data) < limit:
                # exit the while loop
                break

            # increment next call by our timeframe
            start_ts += timeframe

            # sleep after every 3rd call to be kind to the API
            if idx % 3 == 0:
                time.sleep(1)

    def get_ticker(self, **params):
        return self._get('ticker/24hr', data=params)

    def get_symbol_ticker(self, **params):
        return self._get('ticker/price', data=params, version=self.PRIVATE_API_VERSION)

    def get_orderbook_ticker(self, **params):
        return self._get('ticker/bookTicker', data=params, version=self.PRIVATE_API_VERSION)

    # Account Endpoints

    def create_order(self, **params):
        return self._post('order', True, data=params)

    def order_limit(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'type': self.ORDER_TYPE_LIMIT,
            'timeInForce': timeInForce
        })
        return self.create_order(**params)

    def order_limit_buy(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_BUY,
        })
        return self.order_limit(timeInForce=timeInForce, **params)

    def order_limit_sell(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_SELL
        })
        return self.order_limit(timeInForce=timeInForce, **params)

    def order_market(self, **params):
        params.update({
            'type': self.ORDER_TYPE_MARKET
        })
        return self.create_order(**params)

    def order_market_buy(self, **params):
        params.update({
            'side': self.SIDE_BUY
        })
        return self.order_market(**params)

    def order_market_sell(self, **params):
        params.update({
            'side': self.SIDE_SELL
        })
        return self.order_market(**params)

    def create_test_order(self, **params):
        return self._post('order/test', True, data=params)

    def get_order(self, **params):
        return self._get('order', True, data=params)

    def get_all_orders(self, **params):
        return self._get('allOrders', True, data=params)

    def cancel_order(self, **params):
        return self._delete('order', True, data=params)

    def get_open_orders(self, **params):
        return self._get('openOrders', True, data=params)

    # User Stream Endpoints
    def get_account(self, **params):
        return self._get('account', True, data=params)

    def get_asset_balance(self, asset, **params):
        res = self.get_account(**params)
        # find asset balance in list of balances
        if "balances" in res:
            for bal in res['balances']:
                if bal['asset'].lower() == asset.lower():
                    return bal
        return None

    def get_my_trades(self, **params):
        return self._get('myTrades', True, data=params)

    def get_system_status(self):
        return self._request_withdraw_api('get', 'systemStatus.html')

    def get_account_status(self, **params):
        res = self._request_withdraw_api('get', 'accountStatus.html', True, data=params)
        if not res['success']:
            raise BinanceWithdrawException(res['msg'])
        return res

    def get_dust_log(self, **params):
        res = self._request_withdraw_api('get', 'userAssetDribbletLog.html', True, data=params)
        if not res['success']:
            raise BinanceWithdrawException(res['msg'])
        return res

    def get_trade_fee(self, **params):
        res = self._request_withdraw_api('get', 'tradeFee.html', True, data=params)
        if not res['success']:
            raise BinanceWithdrawException(res['msg'])
        return res

    def get_asset_details(self, **params):
        res = self._request_withdraw_api('get', 'assetDetail.html', True, data=params)
        if not res['success']:
            raise BinanceWithdrawException(res['msg'])
        return res

    # Withdraw Endpoints

    def withdraw(self, **params):
        # force a name for the withdrawal if one not set
        if 'asset' in params and 'name' not in params:
            params['name'] = params['asset']
        res = self._request_withdraw_api('post', 'withdraw.html', True, data=params)
        if not res['success']:
            raise BinanceWithdrawException(res['msg'])
        return res

    def get_deposit_history(self, **params):
        return self._request_withdraw_api('get', 'depositHistory.html', True, data=params)

    def get_withdraw_history(self, **params):
        return self._request_withdraw_api('get', 'withdrawHistory.html', True, data=params)

    def get_deposit_address(self, **params):
        return self._request_withdraw_api('get', 'depositAddress.html', True, data=params)

    def get_withdraw_fee(self, **params):
        return self._request_withdraw_api('get', 'withdrawFee.html', True, data=params)

    # User Stream Endpoints

    def stream_get_listen_key(self):
        res = self._post('userDataStream', False, data={})
        return res['listenKey']

    def stream_keepalive(self, listenKey):
        params = {
            'listenKey': listenKey
        }
        return self._put('userDataStream', False, data=params)

    def stream_close(self, listenKey):
        params = {
            'listenKey': listenKey
        }
        return self._delete('userDataStream', False, data=params)

    # Margin Trading Endpoints

    def get_margin_account(self, **params):
        return self._request_margin_api('get', 'margin/account', True, data=params)

    def get_margin_asset(self, **params):
        return self._request_margin_api('get', 'margin/asset', data=params)

    def get_margin_symbol(self, **params):
        return self._request_margin_api('get', 'margin/pair', data=params)

    def get_margin_price_index(self, **params):
        return self._request_margin_api('get', 'margin/priceIndex', data=params)

    def transfer_margin_to_spot(self, **params):
        params['type'] = 2
        return self._request_margin_api('post', 'margin/transfer', signed=True, data=params)

    def transfer_spot_to_margin(self, **params):
        params['type'] = 1
        return self._request_margin_api('post', 'margin/transfer', signed=True, data=params)

    def create_margin_loan(self, **params):
        return self._request_margin_api('post', 'margin/loan', signed=True, data=params)

    def repay_margin_loan(self, **params):
        return self._request_margin_api('post', 'margin/repay', signed=True, data=params)

    def create_margin_order(self, **params):
        return self._request_margin_api('post', 'margin/order', signed=True, data=params)
    
    def margin_order_limit(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'type': self.ORDER_TYPE_LIMIT,
            'timeInForce': timeInForce
        })
        return self.create_margin_order(**params)
    
    def margin_order_limit_buy(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_BUY,
        })
        return self.margin_order_limit(timeInForce=timeInForce, **params)

    def margin_order_limit_sell(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_SELL
        })
        return self.margin_order_limit(timeInForce=timeInForce, **params)

    def cancel_margin_order(self, **params):
        return self._request_margin_api('delete', 'margin/order', signed=True, data=params)

    def get_margin_loan_details(self, **params):
        return self._request_margin_api('get', 'margin/loan', signed=True, data=params)

    def get_margin_repay_details(self, **params):
        return self._request_margin_api('get', 'margin/repay', signed=True, data=params)

    def get_margin_order(self, **params):
        return self._request_margin_api('get', 'margin/order', signed=True, data=params)

    def get_open_margin_orders(self, **params):
        return self._request_margin_api('get', 'margin/openOrders', signed=True, data=params)

    def get_all_margin_orders(self, **params):
        return self._request_margin_api('get', 'margin/allOrders', signed=True, data=params)

    def get_margin_trades(self, **params):
        return self._request_margin_api('get', 'margin/myTrades', signed=True, data=params)

    def get_max_margin_loan(self, **params):
        return self._request_margin_api('get', 'margin/maxBorrowable', signed=True, data=params)

    def get_max_margin_transfer(self, **params):
        return self._request_margin_api('get', 'margin/maxTransferable', signed=True, data=params)

    def margin_stream_get_listen_key(self):
        res = self._request_margin_api('post', 'userDataStream', signed=True)
        return res['listenKey']

    def margin_stream_keepalive(self, listenKey):
        params = {
            'listenKey': listenKey
        }
        return self._request_margin_api('put', 'userDataStream', signed=True, data=params)

    def margin_stream_close(self, listenKey):
        params = {
            'listenKey': listenKey
        }
        return self._request_margin_api('delete', 'userDataStream', signed=True, data=params)
    
    # Futures Trading Endpoints

    def get_futures_account(self, **params):
        return self._request_futures_api('get', 'account', True, data=params)
    
    def get_futures_balance(self, **params):
        return self._request_futures_api('get', 'balance', True, data=params)
    
    def get_futures_exchange_info(self, **params):
        return self._request_futures_api('get', 'exchangeInfo', True, data=params)
    
    def create_futures_order(self, **params):
        return self._request_futures_api('post', 'order', signed=True, data=params)
    
    def futures_order_limit(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'type': self.ORDER_TYPE_LIMIT,
            'timeInForce': timeInForce
        })
        return self.create_futures_order(**params)
    
    def futures_order_limit_buy(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_BUY,
        })
        return self.futures_order_limit(timeInForce=timeInForce, **params)

    def futures_order_limit_sell(self, timeInForce=TIME_IN_FORCE_GTC, **params):
        params.update({
            'side': self.SIDE_SELL
        })
        return self.futures_order_limit(timeInForce=timeInForce, **params)

    def cancel_futures_order(self, **params):
        return self._request_futures_api('delete', 'order', signed=True, data=params)
    
    def futures_position(self, **params):
        return self._request_futures_api('get', 'positionRisk', signed=True, data=params)
    
    def get_open_futures_order(self, **params):
        return self._request_futures_api('get', 'openOrders', signed=True, data=params)
  
    def futures_account_trades(self, **params):
        return self._request_futures_api('get', 'userTrades', signed=True, data=params)
    
    def futures_order_book(self, **params):
        return self._request_futures_api('get', 'depth', signed=True, data=params)
    
    def futures_price_ticker(self, **params):
        return self._request_futures_api('get', 'ticker/price', signed=True, data=params)

    def futures_leverage(self, **params):
        return self._request_futures_api('post', 'leverage', signed=True, data=params)
    
    def futures_index(self, **params):
        return self._request_futures_api('get', 'premiumIndex', signed=True, data=params)
    
    def futures_funding_rate(self, **params):
        return self._request_futures_api('get', 'fundingRate', signed=True, data=params)
    
    def futures_open_interest(self, **params):
        return self._request_futures_api('get', 'openInterest', signed=True, data=params)
