#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Utility functions and classes for theta-e.
'''

from datetime import datetime, timedelta

# ==============================================================================
# Functions
# ==============================================================================

def _get_object(module_class):
    '''
    Given a string with a module class name, it imports and returns the class.
    This function (c) Tom Keffer, weeWX.
    '''
    
    # Split the path into its parts
    parts = module_class.split('.')
    # Strip off the classname:
    module = '.'.join(parts[:-1])
    # Import the top level module
    mod = __import__(module)
    # Recursively work down from the top level module to the class name.
    # Be prepared to catch an exception if something cannot be found.
    try:
        for part in parts[1:]:
            mod = getattr(mod, part)
    except AttributeError:
        # Can't find something. Give a more informative error message:
        raise AttributeError("Module '%s' has no attribute '%s' when searching for '%s'" %
                             (mod.__name__, part, module_class))
    return mod

def getConfig(config_path):
    '''
    Retrieve the config dictionary from config_path.
    '''
    
    import configobj
    try:
        config_dict = configobj.ConfigObj(config_path, file_error=True)
    except IOError:
        print('Error: unable to open configuration file %s' % config_path)
        raise
    except(configobj.ConfigObjError, e):
        print('Error while parsing configuration file %s' % config_path)
        print("    Reason: '%s'" % e)
        raise
    
    try:
        if int(config_dict['debug']) > 1:
            print('Using configuration file %s' % config_path)
    except KeyError:
        config_dict['debug'] = 100
        print('Using configuration file %s' % config_path)
        print("Setting debug level to 100 because apparently you didn't want " +
              "to put it in the config file...")

    return config_dict

def _date_to_datetime(date):
    '''
    Converts a date from string format to datetime object.
    '''
    if date is None:
        return
    if type(date) is str or type(date) is unicode:
        date = datetime.strptime(date, '%Y-%m-%d %H:%M')
    return date

def _date_to_string(date):
    '''
    Converts a date from datetime object to string format.
    '''
    if date is None:
        return
    if type(date) is not str and type(date) is not unicode:
        date = datetime.strftime(date, '%Y-%m-%d %H:%M')
    return date

def _config_date_to_datetime(datestr):
    '''
    Converts a string date from config formatting %Y%m%d to a datetime object.
    '''
    if datestr is None:
        return
    return datetime.strptime(datestr, '%Y%m%d')

def _meso_api_dates(start_date, end_date):
    '''
    Return string-formatted start and end dates for the MesoPy api.
    '''
    start = datetime.strftime(start_date, '%Y%m%d%H%M')
    end = datetime.strftime(end_date, '%Y%m%d%H%M')
    return start, end

def tobool(x):
    """Convert an object to boolean.
    
    Examples:
    >>> print tobool('TRUE')
    True
    >>> print tobool(True)
    True
    >>> print tobool(1)
    True
    >>> print tobool('FALSE')
    False
    >>> print tobool(False)
    False
    >>> print tobool(0)
    False
    >>> print tobool('Foo')
    Traceback (most recent call last):
    ValueError: Unknown boolean specifier: 'Foo'.
    >>> print tobool(None)
    Traceback (most recent call last):
    ValueError: Unknown boolean specifier: 'None'.
    
    This function (c) Tom Keffer, weeWX.
    """

    try:
        if x.lower() in ['true', 'yes']:
            return True
        elif x.lower() in ['false', 'no']:
            return False
    except AttributeError:
        pass
    try:
        return bool(int(x))
    except (ValueError, TypeError):
        pass
    raise ValueError("Unknown boolean specifier: '%s'." % x)

to_bool = tobool

# ==============================================================================
# Classes
# ==============================================================================

import pandas as pd

class TimeSeries():
    def __init__(self, stid):
        self.stid = stid
        self.model = None
        self.data = pd.DataFrame()

class Daily():
    def __init__(self, stid, date):
        self.stid = stid
        self.date = date
        self.model = None
        self.high = None
        self.low = None
        self.wind = None
        self.rain = None
    
    def setValues(self, high, low, wind, rain):
        self.high = high
        self.low = low
        self.wind = wind
        self.rain = rain

class Forecast():
    '''
    Forecast object for a single date. Contains both a timeseries and daily
    values.
    stid and model should be type str; date should be datetime object.
    '''
    
    def __init__(self, stid, model, date):
        self.stid = stid
        self.model = model
        self.date = date
        self.timeseries = TimeSeries(stid)
        self.timeseries.model = model
        self.daily = Daily(stid, date)
        self.daily.model = model

    def setModel(self, model):
        '''
        Changes the model name in the Forecast object and in the embedded
        TimeSeries and Daily.
        '''
        self.model = model
        self.timeseries.model = model
        self.daily.model = model

