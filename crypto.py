# -*- coding: UTF-8 -*-
import logging
from datetime import datetime
import pandas as pd

import ccxt

from base_asset import BaseAsset


class Crypto(BaseAsset):
    def __init__(self, symbol, exchange_name='binance'):
        # For crypto, we use the symbol as the code (e.g., 'BTC/USDT')
        super().__init__(symbol)
        self.symbol = symbol
        self.exchange_name = exchange_name
        self.name = self.symbol.replace('/', '_')  # e.g., BTC/USDT -> BTC_USDT

    def download(self):
        # Initialize the exchange
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class({
            # 'apiKey': '',  # Add your API key if needed
            # 'secret': '',  # Add your secret if needed
            'timeout': 30000,
            # 'enableRateLimit': True,
        })
        
        try:
            # Fetch all available OHLCV data (1 day timeframe)
            # We need to paginate to get all historical data since exchanges have limits
            all_ohlcv = []
            limit = 1000  # Maximum candles per request for most exchanges
            since = None  # Start from the earliest available data
            i = 0
            
            while True:
                i += 1
                try:
                    # Fetch a batch of data - a list of [timestamp, open, high, low, close, volume]
                    if since is None:
                        # First request - get the most recent data
                        ohlcv_batch = exchange.fetch_ohlcv(self.symbol, '1d', limit=limit)
                    else:
                        # Subsequent requests - get data from a specific timestamp
                        ohlcv_batch = exchange.fetch_ohlcv(self.symbol, '1d', since=since, limit=limit)
                    
                    if not ohlcv_batch:
                        logging.warning(f"No data returned for {self.symbol} on batch {i}. Stopping pagination.")
                        break

                    # Prepend older data to the beginning of our list
                    all_ohlcv = ohlcv_batch + all_ohlcv

                    # Check if we've reached the beginning
                    # In this case, this batch may overlap with the previous batch
                    if since != None and ohlcv_batch[0][0] > since:
                        logging.warning(f"We've reached the beginning of available data for {self.symbol}. Stopping pagination.")
                        break

                    # If we got less than the limit, we've reached the end
                    if len(ohlcv_batch) < limit:
                        logging.info(f"Reached the end of available data for {self.symbol} on batch {i}. Stopping pagination.")
                        break

                    # Set since to get older data
                    since = ohlcv_batch[0][0] - (24 * 60 * 60 * 1000 * limit)

                    # Convert since timestamp to human readable format for logging
                    since_date = datetime.fromtimestamp(since / 1000).strftime('%Y-%m-%d %H:%M:%S') if since else 'N/A'
                    first_candle_date = datetime.fromtimestamp(ohlcv_batch[0][0] / 1000).strftime('%Y-%m-%d')
                    last_candle_date = datetime.fromtimestamp(ohlcv_batch[-1][0] / 1000).strftime('%Y-%m-%d')
                    logging.info(f"Fetched {len(ohlcv_batch)} candles for {self.symbol} (batch {i}) from {first_candle_date} to {last_candle_date}, next since: {since_date}")
                        
                except Exception as e:
                    logging.exception(f"Error during pagination for {self.symbol}: {e}")
                    break
            
            if not all_ohlcv:
                raise Exception(f"No data returned for {self.symbol}")
            
            # Convert to DataFrame for easier handling
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Remove duplicates and sort by timestamp
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            
            logging.info(f"Fetched {len(df)} days of historical data for {self.symbol} (from {df['datetime'].iloc[0].strftime('%Y-%m-%d')} to {df['datetime'].iloc[-1].strftime('%Y-%m-%d')})")
            
            # Set worth (closing prices)
            self.worth = df['close'].tolist()
                
        except Exception as e:
            logging.error(f"Error fetching data for {self.symbol}: {e}")
            raise