#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Utility functions and classes for theta-e.
'''

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
