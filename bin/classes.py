#
#
#
#
#

'''
Defines the classes used by the main engine.
'''

class TimeSeries():
    def __init__(self):
        pass

class Daily():
    def __init__(self):
        self.high = np.nan
        self.low = np.nan
        self.wind = np.nan
        self.rain = np.nan

class Forecast(stid, date, source):
    '''
    Forecast object for a single date. Contains both a timeseries and daily values.
    '''
    
    def __init__(self):
        self.stid = stid
        self.source = source
        self.date = date
        self.timeseries = TimeSeries()
        self.daily = Daily()

