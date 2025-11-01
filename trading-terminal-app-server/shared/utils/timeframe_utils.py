"""
Common timeframe utilities for the trading terminal
"""
import datetime



#--------------------------------------- For Indian Market-----------------------------------------
EXCHANGE_MAP = {
    'NSE': 'NSE_EQ',      # NSE Cash
    'BSE': 'BSE_EQ',      # BSE Cash
    'NFO': 'NSE_FNO',     # NSE F&O
    'BFO': 'BSE_FNO',     # BSE F&O
    'MCX': 'MCX_COMM',    # MCX Commodity
    'CDS': 'NSE_CURRENCY',  # NSE Currency
    'BCD': 'BSE_CURRENCY',   # BSE Currency
    'NSE_INDEX': 'IDX_I',  # NSE Index
    'BSE_INDEX': 'IDX_I'   # BSE Index
}


#------------------------------------- for dhan---------------------------
# Exchange mapping for Dhan API

# Time frame mapping for Dhan API
TIMEFRAME_MAP = {
    '1m': '1',    # 1 minute
    '5m': '5',    # 5 minutes
    '15m': '15',  # 15 minutes
    '30m': '25',  # 25 minutes
    '1h': '60',   # 1 hour (60 minutes)
    '2h': '120',  # 2 hours
    '3h': '180',  # 3 hours
    '6h': '360',  # 6 hours
    '1D': 'D',    # Daily data
    'D': 'D'      # Daily data (alternative)
}

# Interval to timeframe mapping for frontend compatibility
INTERVAL_TO_TIMEFRAME = {
    '1m': '1m',
    '3m': '15m',  # Dhan doesn't support 3m, use 15m as closest
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',  # Now maps to 30m
    '1h': '1h',
    '2h': '2h',    # Now supports 2h
    '3h': '3h',    # Now supports 3h
    '4h': '2h',    # Dhan doesn't support 4h, use 2h as closest
    '6h': '6h',    # Now supports 6h
    '8h': '6h',    # Dhan doesn't support 8h, use 6h as closest
    '12h': '6h',   # Dhan doesn't support 12h, use 6h as closest
    '1d': '1D',
    '1D': '1D',
    '3d': '1D',    # Dhan doesn't support 3d, use 1D
    '3D': '1D',    # Dhan doesn't support 3D, use 1D
    '1w': '1D',    # Dhan doesn't support 1w, use 1D
    '1W': '1D',    # Dhan doesn't support 1W, use 1D
    '1M': '1D',    # Dhan doesn't support 1M, use 1D
    '3M': '1D',    # Dhan doesn't support 3M, use 1D
    '1Y': '1D'     # Dhan doesn't support 1Y, use 1D
}

def get_dhan_exchange_segment(exchange):
    """Convert exchange name to Dhan exchange segment"""
    return EXCHANGE_MAP.get(exchange, 'NSE_EQ')

def get_dhan_timeframe(timeframe):
    """Convert timeframe to Dhan timeframe format"""
    return TIMEFRAME_MAP.get(timeframe, '1')

def validate_trading_params(exchange, timeframe):
    """Validate exchange and timeframe parameters"""
    if exchange not in EXCHANGE_MAP:
        return False, f"Invalid exchange: {exchange}. Valid exchanges: {list(EXCHANGE_MAP.keys())}"
    
    if timeframe not in TIMEFRAME_MAP:
        return False, f"Invalid timeframe: {timeframe}. Valid timeframes: {list(TIMEFRAME_MAP.keys())}"
    
    return True, "Valid parameters"

def get_timeframe_based_dates(timeframe):
    """Get appropriate date range based on timeframe"""
    # Get current date and time
    now = datetime.datetime.now()
    
    # Define date ranges based on timeframe
    timeframe_ranges = {
        '1m': {
            'days_back': 1,  # Last 1 day for 1-minute data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '5m': {
            'days_back': 3,  # Last 3 days for 5-minute data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '15m': {
            'days_back': 7,  # Last 7 days for 15-minute data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '30m': {
            'days_back': 10,  # Last 10 days for 30-minute data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '1h': {
            'days_back': 30,  # Last 30 days for 1-hour data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '2h': {
            'days_back': 60,  # Last 60 days for 2-hour data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '3h': {
            'days_back': 90,  # Last 90 days for 3-hour data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '6h': {
            'days_back': 180,  # Last 180 days for 6-hour data
            'start_time': '09:30:00',
            'end_time': '15:30:00'
        },
        '1D': {
            'days_back': 90,  # Last 90 days for daily data
            'start_time': '00:00:00',
            'end_time': '23:59:59'
        },
        'D': {
            'days_back': 90,  # Last 90 days for daily data
            'start_time': '00:00:00',
            'end_time': '23:59:59'
        }
    }
    
    # Get range for the timeframe, default to 1m if not found
    range_config = timeframe_ranges.get(timeframe, timeframe_ranges['1m'])
    
    # Calculate start date
    start_date = now - datetime.timedelta(days=range_config['days_back'])
    
    # Format dates
    from_date = start_date.strftime('%Y-%m-%d') + ' ' + range_config['start_time']
    to_date = now.strftime('%Y-%m-%d') + ' ' + range_config['end_time']
    
    return from_date, to_date

def map_interval_to_timeframe(interval):
    """Map frontend interval to Dhan timeframe"""
    return INTERVAL_TO_TIMEFRAME.get(interval, '1m')

def get_timeframe_ranges_info():
    """Get timeframe-based date ranges for reference"""
    now = datetime.datetime.now()
    
    # Define date ranges based on timeframe
    timeframe_ranges = {
        '1m': {
            'days_back': 1,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 1 day for 1-minute data'
        },
        '5m': {
            'days_back': 3,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 3 days for 5-minute data'
        },
        '15m': {
            'days_back': 7,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 7 days for 15-minute data'
        },
        '30m': {
            'days_back': 10,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 10 days for 30-minute data'
        },
        '1h': {
            'days_back': 30,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 30 days for 1-hour data'
        },
        '2h': {
            'days_back': 60,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 60 days for 2-hour data'
        },
        '3h': {
            'days_back': 90,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 90 days for 3-hour data'
        },
        '6h': {
            'days_back': 180,
            'start_time': '09:30:00',
            'end_time': '15:30:00',
            'description': 'Last 180 days for 6-hour data'
        },
        '1D': {
            'days_back': 90,
            'start_time': '00:00:00',
            'end_time': '23:59:59',
            'description': 'Last 90 days for daily data'
        },
        'D': {
            'days_back': 90,
            'start_time': '00:00:00',
            'end_time': '23:59:59',
            'description': 'Last 90 days for daily data'
        }
    }
    
    # Calculate actual date ranges
    ranges_info = {}
    for timeframe, config in timeframe_ranges.items():
        start_date = now - datetime.timedelta(days=config['days_back'])
        from_date = start_date.strftime('%Y-%m-%d') + ' ' + config['start_time']
        to_date = now.strftime('%Y-%m-%d') + ' ' + config['end_time']
        
        ranges_info[timeframe] = {
            'description': config['description'],
            'days_back': config['days_back'],
            'from_date': from_date,
            'to_date': to_date,
            'start_time': config['start_time'],
            'end_time': config['end_time']
        }
    
    return {
        "current_time": now.strftime('%Y-%m-%d %H:%M:%S'),
        "timeframe_ranges": ranges_info,
        "note": "These are default ranges when no custom dates are provided"
    }

def get_exchange_options():
    """Get exchange options for dropdowns"""
    return [
        {"value": key, "label": f"{key} - {value}"} 
        for key, value in EXCHANGE_MAP.items()
    ]

def get_timeframe_options():
    """Get timeframe options for dropdowns"""
    return [
        {"value": key, "label": f"{key} ({value})"} 
        for key, value in TIMEFRAME_MAP.items()
    ]

def get_interval_options():
    """Get interval options for frontend dropdowns"""
    return [
        {"value": key, "label": f"{key} -> {value}"} 
        for key, value in INTERVAL_TO_TIMEFRAME.items()
    ] 