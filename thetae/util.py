#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Utility functions and classes for theta-e.
"""

from datetime import datetime, timedelta
import os
import numpy as np
import pandas as pd


# ==============================================================================
# Classes
# ==============================================================================

class TimeSeries(object):
    """
    TimeSeries object, which is really just a wrapper for a pandas DataFrame.
    """

    def __init__(self, stid):
        self.stid = stid
        self.model = None
        self.data = pd.DataFrame()


class Daily(object):
    """
    Daily object, which contains high, low, wind, and rain for a specific date.
    """

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


class Forecast(object):
    """
    Forecast object for a single date. Contains both a timeseries and daily objects.
    stid and model should be type str; date should be datetime object.
    """

    def __init__(self, stid, model, date):
        self.stid = stid
        self.model = model
        self.date = date
        self.timeseries = TimeSeries(stid)
        self.timeseries.model = model
        self.daily = Daily(stid, date)
        self.daily.model = model

    def setModel(self, model):
        """
        Changes the model name in the Forecast object and in the embedded
        TimeSeries and Daily.
        """
        self.model = model
        self.timeseries.model = model
        self.daily.model = model
        return self


# ==============================================================================
# General utility functions
# ==============================================================================

def get_object(module_class):
    """
    Given a string with a module class name, it imports and returns the class.
    This function (c) Tom Keffer, weeWX; modified by Jonathan Weyn.
    """
    # Split the path into its parts
    parts = module_class.split('.')
    # Get the top level module
    module = parts[0]  # '.'.join(parts[:-1])
    # Import the top level module
    mod = __import__(module)
    # Recursively work down from the top level module to the class name.
    # Be prepared to catch an exception if something cannot be found.
    try:
        for part in parts[1:]:
            module = '.'.join([module, part])
            # Import each successive module
            __import__(module)
            mod = getattr(mod, part)
    except ImportError as e:
        # Can't find a recursive module. Give a more informative error message:
        raise ImportError("'%s' raised when searching for %s" % (str(e), module))
    except AttributeError:
        # Can't find the last attribute. Give a more informative error message:
        raise AttributeError("Module '%s' has no attribute '%s' when searching for '%s'" %
                             (mod.__name__, part, module_class))

    return mod


def get_config(config_path):
    """
    Retrieve the config dictionary from config_path.
    """
    import configobj
    try:
        config_dict = configobj.ConfigObj(config_path, file_error=True)
    except IOError:
        print('Error: unable to open configuration file %s' % config_path)
        raise
    except configobj.ConfigObjError as e:
        print('Error while parsing configuration file %s' % config_path)
        print("*** Reason: '%s'" % e)
        raise

    # Make sure debug level is there
    try:
        config_dict['debug'] = int(config_dict['debug'])
    except KeyError:
        config_dict['debug'] = 1
        print("Setting debug level to 1 because apparently you didn't want "
              "to put it in the config file...")
    except ValueError:
        config_dict['debug'] = 1
        print("Invalid debugging level specified; setting debug level to 1.")
    if config_dict['debug'] > 1:
        print('Using configuration file %s' % config_path)

    # Make sure traceback is there
    try:
        config_dict['traceback'] = to_bool(config_dict['traceback'])
    except KeyError:
        config_dict['traceback'] = False
    if int(config_dict['debug']) > 1 and config_dict['traceback']:
        print('Using traceback option: program will crash upon exception raised.')

    return config_dict


def get_codes(codes_file, stid=None):
    """
    Return a dict-format index of codes in codes_file for data sources where necessary. The file is expected to be
    comma-separated values with one header row. If more than one code (i.e. column) per site is given, then the value
    of the exported dictionary is a tuple of all the codes. Codes values are returned as string types. If stid is
    provided, then only the codes for that station ID are returned; otherwise, the entire dictionary is returned.

    :param codes_file: str: CSV file path
    :param stid: str: if given, only returns the codes for a specific stid
    :return: codes_dict or codes: dictionary of codes, or code values for a station ID
    """
    codes_array = np.genfromtxt(codes_file, dtype='str', delimiter=',', skip_header=1)
    num_sites, num_codes = codes_array.shape
    num_codes -= 1  # remove the column for stid
    codes_dict = {}
    for s in range(num_sites):
        site = codes_array[s, 0].upper()
        if num_codes == 1:
            codes_dict[site] = codes_array[s, 1]
        else:
            codes_dict[site] = tuple(codes_array[s, 1:])
    if stid is not None:
        return codes_dict[stid]
    else:
        return codes_dict


def date_to_datetime(date):
    """
    Converts a date from string format to datetime object.
    """
    if date is None:
        return
    if type(date) is str or type(date) is unicode:  # UNICODE only in Python 2
        date = datetime.strptime(date, '%Y-%m-%d %H:%M')
    return date


def date_to_string(date):
    """
    Converts a date from datetime object to string format.
    """
    if date is None:
        return
    if type(date) is not str and type(date) is not unicode:
        date = datetime.strftime(date, '%Y-%m-%d %H:%M')
    return date


def config_date_to_datetime(date_str):
    """
    Converts a string date from config formatting %Y%m%d to a datetime object.
    """
    if date_str is None:
        return
    return datetime.strptime(date_str, '%Y%m%d')


def meso_api_dates(start_date, end_date):
    """
    Return string-formatted start and end dates for the MesoPy api.
    """
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


def get_ghcn_stid(stid, THETAE_ROOT='.'):
    """
    After code by Luke Madaus.

    Gets the GHCN station ID from the 4-letter station ID.
    """
    main_addr = 'ftp://ftp.ncdc.noaa.gov/pub/data/noaa'

    site_directory = '%s/site_data' % THETAE_ROOT
    if not (os.path.isdir(site_directory)):
        os.system('mkdir -p %s' % site_directory)
    # Check to see that ish-history.txt exists
    stations_file = 'isd-history.txt'
    stations_filename = '%s/%s' % (site_directory, stations_file)
    if not os.path.exists(stations_filename):
        print('get_ghcn_stid: downloading site name database')
        os.system('wget --directory-prefix=%s %s/%s' % (site_directory, main_addr, stations_file))

    # Now open this file and look for our siteid
    site_found = False
    infile = open(stations_filename, 'r')
    station_wbans = []
    station_ghcns = []
    for line in infile:
        if stid.upper() in line:
            linesp = line.split()
            if (not linesp[0].startswith('99999') and not site_found
                    and not linesp[1].startswith('99999')):
                try:
                    site_wban = int(linesp[0])
                    station_ghcn = int(linesp[1])
                    # site_found = True
                    print('get_ghcn_stid: site found for %s (%s)' %
                          (stid, station_ghcn))
                    station_wbans.append(site_wban)
                    station_ghcns.append(station_ghcn)
                except:
                    continue
    if len(station_wbans) == 0:
        raise ValueError('get_ghcn_stid error: so station found for %s' % stid)

    # Format station as USW...
    usw_format = 'USW000%05d'
    return usw_format % station_ghcns[0]


# ==============================================================================
# Unit conversion functions
# ==============================================================================

def c_to_f(val):
    """
    Converts celsius to integer fahrenheit; accepts numeric or string
    """
    return int(float(val) * 9 / 5 + 32)


def mph_to_kt(val):
    """
    Converts mph to knots; accepts numeric or string
    """
    return int(float(val) * 0.868976)


def wind_dir_to_deg(val):
    """
    Converts string winds to float degrees
    """
    dirtxt = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')
    dirdeg = [22.5 * x for x in range(len(dirtxt))]
    wdir_convert = dict(zip(dirtxt, dirdeg))
    return wdir_convert[val]


def dewpoint_from_t_rh(t, rh):
    """
    Calculate dewpoint in C from temperature in C and relative humidity in %.

    :param t: temperature in C
    :param rh: relative humidity in %
    :return: dewpoint: dewpoint in C
    """
    dewpoint = (243.04 * (np.log(rh/100.) + ((17.625 * t) / (243.04 + t))) /
                (17.625 - np.log(rh/100.) - ((17.625 * t) / (243.04 + t))))
    return dewpoint
