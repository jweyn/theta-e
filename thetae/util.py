#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Utility functions and classes for theta-e.
"""

from datetime import datetime, timedelta
import pytz
import os
import numpy as np
import pandas as pd
from builtins import str
try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen


# ==================================================================================================================== #
# Classes
# ==================================================================================================================== #

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
        self.high = to_float(high)
        self.low = to_float(low)
        self.wind = to_float(wind)
        self.rain = to_float(rain)

    def getValues(self):
        return self.high, self.low, self.wind, self.rain


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


# ==================================================================================================================== #
# General utility functions
# ==================================================================================================================== #

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


def write_codes(config, codes_dict, codes_file, header='station ID,'):
    """
    Write a codes dictionary to a file of comma-separated values with one header row, given by 'header'. For use when a
    data source can provide a needed code but a cache is useful. The dictionary is expected to have station IDs as keys
    and either strings or tuples of strings as items, just like the output of get_codes().

    :param config:
    :param codes_dict: dict: dictionary of codes to write, where keys are station IDs
    :param codes_file: str: CSV file name (located within THETAE_ROOT/codes)
    :param header: str: the descriptive header row
    :return:
    """
    codes_directory = '%s/codes' % config['THETAE_ROOT']
    if not(os.path.isdir(codes_directory)):
        os.makedirs(codes_directory)
    codes_file_name = '%s/%s' % (codes_directory, codes_file)
    num_keys = len(list(codes_dict.keys()))
    if type(codes_dict[list(codes_dict.keys())[0]]) is tuple:
        num_codes = len(codes_dict[list(codes_dict.keys())[0]])
    else:
        num_codes = 1
    codes_array = np.empty((num_keys, num_codes + 1), dtype=object)
    row = 0
    for key, code in codes_dict.items():
        codes_array[row, 0] = key
        codes_array[row, 1:] = code
        row += 1
    np.savetxt(codes_file_name, codes_array, fmt='%s', delimiter=',', header=header)


def get_codes(config, codes_file, stid=None):
    """
    Return a dict-format index of codes in codes_file for data sources where necessary. The file is expected to be
    comma-separated values with one header row. If more than one code (i.e. column) per site is given, then the value
    of the exported dictionary is a tuple of all the codes. Codes values are returned as string types. If stid is
    provided, then only the codes for that station ID are returned; otherwise, the entire dictionary is returned.

    :param config:
    :param codes_file: str: CSV file name (located within THETAE_ROOT/codes)
    :param stid: str: if given, only returns the codes for a specific stid
    :return: codes_dict or codes: dictionary of codes, or code values for a station ID
    """
    codes_file_name = '%s/codes/%s' % (config['THETAE_ROOT'], codes_file)
    codes_array = np.genfromtxt(codes_file_name, dtype='str', delimiter=',', skip_header=1)
    if len(codes_array.shape) == 1:
        codes_array = np.expand_dims(codes_array, axis=0)
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


def write_ensemble_daily(config, forecasts, ensemble_file):
    """
    Writes ensemble daily forecast data, provided in the form of a list of Forecast or Daily objects, for tomorrow's
    forecast. The specific file should be provided in the 'Models' section of config. The function read_ensemble_daily
    can be used to read the file generated from this function, e.g. to generate plots.

    :param config:
    :param forecasts: list: list of Forecast objects
    :param ensemble_file: str: CSV file name (located within THETAE_ROOT/site_data)
    :return:
    """
    ensemble_file_name = '%s/site_data/%s' % (config['THETAE_ROOT'], ensemble_file)
    header = 'date,model,high,low,wind,rain'
    num_forecasts = len(forecasts)
    daily_array = np.empty((num_forecasts, 6), dtype=object)
    for f in range(num_forecasts):
        daily_array[f, 0] = date_to_string(forecasts[f].date)
        daily_array[f, 1] = forecasts[f].model
        try:
            daily_array[f, 2:] = forecasts[f].daily.getValues()
        except AttributeError:
            daily_array[f, 2:] = forecasts[f].getValues()
    np.savetxt(ensemble_file_name, daily_array, fmt='%s', delimiter=',', header=header)


def read_ensemble_daily(config, ensemble_file, stid=None, forecast_date=None):
    """
    Generates a list of Daily objects from a specified file (as generated by write_ensemble_daily).

    :param config:
    :param ensemble_file: str: CSV file name (located within THETAE_ROOT/site_data)
    :param stid: str: station ID
    :return: list: list of Daily objects
    """
    ensemble_file_name = '%s/site_data/%s' % (config['THETAE_ROOT'], ensemble_file)
    daily_array = np.genfromtxt(ensemble_file_name, dtype='str', delimiter=',', skip_header=1)
    ensemble_date = date_to_datetime(daily_array[0][0])
    dailys = []
    if stid is None:
        stid = config['current_stid']
    if forecast_date is None:
        forecast_date = ensemble_date
    else:
        # Raise an error if the requested forecast date is not the one in the file
        if date_to_datetime(forecast_date) != ensemble_date:
            raise ValueError('Requested forecast date does not match that in file (%s)' % ensemble_date)
        
    for day in range(daily_array.shape[0]):
        daily = Daily(stid, forecast_date)
        daily.model = daily_array[day, 0]
        daily.setValues(*tuple(daily_array[day, 2:]))
        dailys.append(daily)

    return dailys


def get_ghcn_stid(config, stid):
    """
    After code by Luke Madaus.

    Gets the GHCN station ID from the 4-letter station ID.
    """
    main_addr = 'ftp://ftp.ncdc.noaa.gov/pub/data/noaa'

    site_directory = '%s/site_data' % config['THETAE_ROOT']
    # Check to see that ish-history.txt exists
    stations_file = 'isd-history.txt'
    stations_filename = '%s/%s' % (site_directory, stations_file)
    if not os.path.exists(stations_filename):
        print('get_ghcn_stid: downloading site name database')
        try:
            response = urlopen('%s/%s' % (main_addr, stations_file))
            with open(stations_filename, 'w') as f:
                f.write(response.read())
        except BaseException as e:
            print('get_ghcn_stid: unable to download site name database')
            print("*** Reason: '%s'" % str(e))
            if config['traceback']:
                raise

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


def check_cache_file(config, file_name, interval=12, get_23z=True):
    """
    Check that a cache file (such as for an API) exists and is recent enough to be used.

    :param config:
    :param file_name: str: name of file located within THETAE_ROOT/site_data
    :param interval: int: caching interval in hours, i.e., maximum allowed age of file
    :param get_23z: bool: if True, sets the maximum age of the cache to 1 hour if the time is past 23Z
    :return:
    """
    time_now = datetime.utcnow()
    if time_now.hour == 23 and get_23z:
        recent = timedelta(hours=1)
    else:
        recent = timedelta(hours=interval)
    cache_ok = False
    try:
        modified_time = file_mtime_utc(file_name)
        if time_now - modified_time > recent:
            if config['debug'] > 9:
                print('check_cache_file: %s too old' % file_name)
        else:
            cache_ok = True
    except BaseException as e:
        if config['debug'] > 9:
            print("check_cache_file: '%s'" % str(e))
    return cache_ok


# ==================================================================================================================== #
# Type conversion functions
# ==================================================================================================================== #

def date_to_datetime(date):
    """
    Converts a date from string format to datetime object.
    """
    try:
        return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except:
        return date


def date_to_string(date):
    """
    Converts a date from datetime object to string format.
    """
    try:
        return str(date)
    except:
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
    start = str(datetime.strftime(start_date, '%Y%m%d%H%M'))
    end = str(datetime.strftime(end_date, '%Y%m%d%H%M'))
    return start, end


def localized_date_to_utc(date):
    """
    Return a timezone-unaware UTC time from a timezone-aware localized datetime object.
    """
    if not isinstance(date, datetime):
        return date
    return date.astimezone(pytz.utc).replace(tzinfo=None)


def epoch_time_to_datetime(timestamp, timezone=None):
    """
    Return a timezone-unaware datetime from an epoch time representation. If timezone string is provided, then
    localized_date_to_utc will be applied on the resulting datetime object.
    """
    date = datetime.fromtimestamp(timestamp)
    if timezone is not None:
        tz = pytz.timezone(timezone)
        date = tz.localize(date)
        return date.astimezone(pytz.utc).replace(tzinfo=None)
    return date


def last_leap_year(date=None):
    """
    Return the last complete leap year from today or a specified date.
    """
    if date is None:
        date = datetime.utcnow()
    leap = (date.year - 1) - ((date.year - 1) % 4)
    return leap


def file_mtime_utc(file_name):
    """
    Return a timezone-unaware datetime in UTC for the last modified time of a file.
    """
    mtime = os.path.getmtime(file_name)
    date = datetime.utcfromtimestamp(mtime)
    return date.replace(tzinfo=None)


def to_bool(x):
    """Convert an object to boolean.
    
    Examples:
    >>> print to_bool('TRUE')
    True
    >>> print to_bool(True)
    True
    >>> print to_bool(1)
    True
    >>> print to_bool('FALSE')
    False
    >>> print to_bool(False)
    False
    >>> print to_bool(0)
    False
    >>> print to_bool('Foo')
    Traceback (most recent call last):
    ValueError: Unknown boolean specifier: 'Foo'.
    >>> print to_bool(None)
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


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ==================================================================================================================== #
# Unit conversion functions
# ==================================================================================================================== #

def c_to_f(val):
    """
    Converts Celsius to Fahrenheit; accepts numeric or string
    """
    try:
        return float(val) * 9. / 5. + 32.
    except (TypeError, ValueError):
        return val * 9. / 5. + 32.


def f_to_c(val):
    """
    Converts Fahrenheit to Celsius; accepts numeric or string
    """
    try:
        return (float(val) - 32.) * 5. / 9.
    except (TypeError, ValueError):
        return (val - 32.) * 5. / 9.


def mph_to_kt(val):
    """
    Converts mph to knots; accepts numeric or string
    """
    try:
        return int(float(val) * 0.868976)
    except (TypeError, ValueError):
        return val * 0.868976


def ms_to_kt(val):
    """
    Converts m/s to knots; accepts numeric or string
    """
    try:
        return float(val) * 1.94384
    except (TypeError, ValueError):
        return val * 1.94384


def inhg_to_mb(val):
    """
    Converts inches of mercury to millibars; accepts numeric or string
    """
    try:
        return float(val) * 33.8639
    except (TypeError, ValueError):
        return val * 33.8639


def mm_to_in(val):
    """
    Converts millimeters to inches; accepts numeric or string
    """
    try:
        return float(val) * 0.0393701
    except (TypeError, ValueError):
        return val * 0.0393701


def wind_dir_to_deg(val):
    """
    Converts string wind to float degrees
    """
    dir_text = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW')
    dir_deg = [22.5 * x for x in range(len(dir_text))]
    conversion = dict(zip(dir_text, dir_deg))
    return conversion[val]


def wind_uv_to_speed_dir(uval, vval):
    """
    Converts U and V component of wind to a speed and direction
    """
    vel_val = np.sqrt(uval**2 + vval**2)
    wdir = 180/np.pi * np.arctan2(uval, vval)
    wdir += 180
    if wdir < 0:
        wdir += 360
    return vel_val, wdir


def dewpoint_from_t_rh(t, rh, is_f=False):
    """
    Calculate dewpoint from temperature relative humidity in %.

    :param t: temperature in C
    :param rh: relative humidity in %
    :param is_f: if True, temperature is in Fahrenheit, otherwise, Celsius
    :return: dewpoint: dewpoint in specified temperature units
    """
    if is_f:
        t = f_to_c(t)
    dewpoint = (243.04 * (np.log(rh/100.) + ((17.625 * t) / (243.04 + t))) /
                (17.625 - np.log(rh/100.) - ((17.625 * t) / (243.04 + t))))
    if is_f:
        return c_to_f(dewpoint)
    else:
        return dewpoint
