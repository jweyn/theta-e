#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve verification from MesoWest, NWS CF6 files, and NCDC data.
"""

from .MesoPy import Meso
from .obs import get_obs
import pandas as pd
import numpy as np
import os
import re
from thetae.util import meso_api_dates, Daily, check_cache_file
from thetae.db import readTimeSeries, get_latest_date
from thetae import MissingDataError
from datetime import datetime, timedelta
import requests
from builtins import str


def get_cf6_files(config, stid, num_files=1):
    """
    After code by Luke Madaus

    Retrieves CF6 climate verification data released by the NWS. Parameter num_files determines how many recent files
    are downloaded.
    """
    # Create directory if it does not exist
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    if config['debug'] > 50:
        print('get_cf6_files: accessing site data in %s' % site_directory)

    # Construct the web url address. Check if a special 3-letter station ID is provided.
    nws_url = 'http://forecast.weather.gov/product.php?site=NWS&issuedby=%s&product=CF6&format=TXT'
    try:
        stid3 = config['Stations'][stid]['station_id3']
    except KeyError:
        stid3 = stid[1:].upper()
    nws_url = nws_url % stid3

    # Determine how many files (iterations of product) we want to fetch
    if num_files == 1:
        print('get_cf6_files: retrieving latest CF6 file for %s' % stid)
    else:
        print('get_cf6_files: retrieving %s archived CF6 files for %s' % (num_files, stid))

    # Fetch files
    for r in range(1, num_files + 1):
        # Format the web address: goes through 'versions' on NWS site which correspond to increasingly older files
        version = 'version=%d&glossary=0' % r
        nws_site = '&'.join((nws_url, version))
        if config['debug'] > 50:
            print('get_cf6_files: fetching from %s' % nws_site)
        response = requests.get(nws_site)
        cf6_data = response.text

        # Remove the header
        try:
            body_and_footer = cf6_data.split('CXUS')[1]  # Mainland US
        except IndexError:
            try:
                body_and_footer = cf6_data.split('CXHW')[1]  # Hawaii
            except IndexError:
                try:
                    body_and_footer = cf6_data.split('CXAK')[1]  # Alaska
                except IndexError:
                    if config['debug'] > 50:
                        print('get_cf6_files: bad file from request version %d' % r)
                    continue
        body_and_footer_lines = body_and_footer.splitlines()
        if len(body_and_footer_lines) <= 2:
            body_and_footer = cf6_data.split('000')[2]

        # Remove the footer
        body = body_and_footer.split('[REMARKS]')[0]

        # Find the month and year of the file
        try:
            current_year = re.search('YEAR: *(\d{4})', body).groups()[0]
        except BaseException:
            if config['debug'] > 9:
                print('get_cf6_files warning: file from request version %d is faulty' % r)
            continue
        try:
            current_month = re.search('MONTH: *(\D{3,9})', body).groups()[0]
            current_month = current_month.strip()  # Gets rid of newlines and whitespace
            datestr = '%s %s' % (current_month, current_year)
            file_date = datetime.strptime(datestr, '%B %Y')
        except:  # Some files have a different formatting, although this may be fixed now.
            current_month = re.search('MONTH: *(\d{2})', body).groups()[0]
            current_month = current_month.strip()
            datestr = '%s %s' % (current_month, current_year)
            file_date = datetime.strptime(datestr, '%m %Y')

        # Write to a temporary file, check if output file exists, and if so, make sure the new one has more data
        datestr = file_date.strftime('%Y%m')
        filename = '%s/%s_%s.cli' % (site_directory, stid.upper(), datestr)
        temp_file = '%s/temp.cli' % site_directory
        with open(temp_file, 'w') as out:
            out.write(body)

        def file_len(file_name):
            with open(file_name) as f:
                for i, l in enumerate(f):
                    pass
                return i + 1

        if os.path.isfile(filename):
            old_file_len = file_len(filename)
            new_file_len = file_len(temp_file)
            if old_file_len < new_file_len:
                if config['debug'] > 9:
                    print('get_cf6_files: overwriting %s' % filename)
                os.remove(filename)
                os.rename(temp_file, filename)
            else:
                if config['debug'] > 9:
                    print('get_cf6_files: %s already exists' % filename)
        else:
            if config['debug'] > 9:
                print('get_cf6_files: writing %s' % filename)
            os.rename(temp_file, filename)


def _cf6_wind(config, stid):
    """
    After code by Luke Madaus

    This function is used internally only.

    Generates wind verification values from climate CF6 files stored in site_directory. These files can be generated
    by _get_cf6_files.
    """
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    if config['debug'] > 9:
        print('verification: searching for CF6 files in %s' % site_directory)
    listing = os.listdir(site_directory)
    file_list = [f for f in listing if f.startswith(stid.upper()) and f.endswith('.cli')]
    file_list.sort()
    if len(file_list) == 0:
        raise IOError('No CF6 files found in %s for site %s.' % (site_directory, stid))
    if config['debug'] > 50:
        print('verification: found %d CF6 files' % len(file_list))

    # Interpret CF6 files
    if config['debug'] > 50:
        print('verification: reading CF6 files')
    cf6_values = {}
    for file in file_list:
        year, month = re.search('(\d{4})(\d{2})', file).groups()
        open_file = open('%s/%s' % (site_directory, file), 'r')
        for line in open_file:
            matcher = re.compile('( \d|\d{2}) ( \d{2}|-\d{2}|  \d| -\d|\d{3})')
            if matcher.match(line):
                # We've found an obs line!
                lsp = line.split()
                day = int(lsp[0])
                date = datetime(int(year), int(month), day)
                cf6_values[date] = {}
                # Get only the wind value
                if lsp[11] == 'M':
                    cf6_values[date]['wind'] = 0.0
                else:
                    cf6_values[date]['wind'] = float(lsp[11]) * 0.868976

    return cf6_values


def _climo_wind(config, stid, dates=None):
    """
    This function is used internally only.

    Fetches climatological wind data using ulmo package to retrieve NCDC archives.
    """
    import ulmo
    from thetae.util import get_ghcn_stid

    ghcn_stid = get_ghcn_stid(config, stid)

    if config['debug'] > 0:
        print('verification: fetching wind data for %s from NCDC (may take a while)' % ghcn_stid)
    v = 'WSF2'
    D = ulmo.ncdc.ghcn_daily.get_data(ghcn_stid, as_dataframe=True, elements=[v])
    wind_dict = {}
    if dates is None:
        dates = list(D[v].index.to_timestamp().to_pydatetime())
    for date in dates:
        wind_dict[date] = {'wind': D[v].loc[date]['value'] / 10. * 1.94384}

    return wind_dict


def get_verification(config, stid, start_dt, end_dt, use_climo=False, use_cf6=True):
    """
    Generates verification data from MesoWest API. If use_climo is True, then fetch climate data from NCDC using ulmo
    to fill in wind values. (We probably generally don't want to do this, because it is slow and is delayed by 1-2
    weeks from present.) If use_cf6 is True, then any CF6 files found in ~/site_data will be used for wind values.
    These files are retrieved by get_cf6_files.
    """
    # MesoWest token and init
    meso_token = config['Verify']['api_key']
    m = Meso(token=meso_token)

    # Look for desired variables
    vars_request = ['air_temp_low_6_hour', 'air_temp_high_6_hour', 'precip_accum_six_hour']
    vars_api = ','.join(vars_request)

    # Units
    units = 'temp|f,precip|in,speed|kts'

    # Retrieve 6-hourly data
    start, end = meso_api_dates(start_dt, end_dt)
    print('verification: retrieving 6-hourly data from %s to %s' % (start, end))
    obs = m.timeseries(stid=stid, start=start, end=end, vars=vars_api, units=units, hfmetars='0')
    obs_6hour = pd.DataFrame.from_dict(obs['STATION'][0]['OBSERVATIONS'])

    # Rename columns to requested vars. This changes the columns in the DataFrame to corresponding names in
    # vars_request, because otherwise the columns returned by MesoPy are weird.
    obs_var_names = obs['STATION'][0]['SENSOR_VARIABLES']
    obs_var_keys = list(obs_var_names.keys())
    col_names = list(map(''.join, obs_6hour.columns.values))
    for c in range(len(col_names)):
        col = col_names[c]
        for k in range(len(obs_var_keys)):
            key = obs_var_keys[k]
            if col == list(obs_var_names[key].keys())[0]:
                col_names[c] = key
    obs_6hour.columns = col_names

    # Let's add a check here to make sure that we do indeed have all of the variables we want
    for var in vars_request + ['wind_speed']:
        if var not in col_names:
            obs_6hour = obs_6hour.assign(**{var: np.nan})

    # Change datetime column to datetime object, subtract 6 hours to use 6Z days
    dateobj = pd.Index(pd.to_datetime(obs_6hour['date_time'])).tz_localize(None) - timedelta(hours=6)
    obs_6hour['date_time'] = dateobj
    datename = 'DATETIME'
    obs_6hour = obs_6hour.rename(columns={'date_time': datename})

    # Now we're going to group the data into daily values.
    # Define an aggregation function for pandas groupby
    def day(dt):
        d = dt.iloc[0]
        return datetime(d.year, d.month, d.day)

    aggregate = {datename: day}
    aggregate['air_temp_high_6_hour'] = np.max
    aggregate['air_temp_low_6_hour'] = np.min
    aggregate['wind_speed'] = np.max
    aggregate['precip_accum_six_hour'] = np.sum

    # Now group by day. Note that we changed the time to subtract 6 hours, so days are nicely defined as 6Z to 6Z.
    if config['debug'] > 50:
        print('verification: grouping data by day')
    obs_daily = obs_6hour.groupby([pd.DatetimeIndex(obs_6hour[datename]).year,
                                   pd.DatetimeIndex(obs_6hour[datename]).month,
                                   pd.DatetimeIndex(obs_6hour[datename]).day]).agg(aggregate)

    # Now we check for wind values from the CF6 files, which are the actual verification
    if use_climo or use_cf6:
        if config['debug'] > 9:
            print('verification: checking climo and/or CF6 for wind data')
        climo_values = {}
        cf6_values = {}
        if use_climo:
            try:
                climo_values = _climo_wind(config, stid)
            except BaseException as e:
                print('verification warning: problem reading climo data')
                print("*** Reason: '%s'" % str(e))
        if use_cf6:
            try:
                cf6_values = _cf6_wind(config, stid)
            except BaseException as e:
                print('verification warning: problem reading CF6 files')
                print("*** Reason: '%s'" % str(e))
        climo_values.update(cf6_values)  # CF6 overrides
        count_rows = 0
        for index, row in obs_daily.iterrows():
            date = row[datename]
            if date in climo_values.keys():
                count_rows += 1
                obs_wind = row['wind_speed']
                cf6_wind = climo_values[date]['wind']
                if obs_wind - cf6_wind >= 5:
                    if config['debug'] > 9:
                        print('verification warning: obs wind for %s (%0.0f) much larger than '
                              'cf6/climo wind (%0.0f); using obs' % (date, obs_wind, cf6_wind))
                else:
                    obs_daily.loc[index, 'wind_speed'] = cf6_wind
        if config['debug'] > 9:
            print('verification: found %d matching rows for wind' % count_rows)

    # Rename the columns
    obs_daily.rename(columns={'air_temp_high_6_hour': 'high'}, inplace=True)
    obs_daily.rename(columns={'air_temp_low_6_hour': 'low'}, inplace=True)
    obs_daily.rename(columns={'wind_speed': 'wind'}, inplace=True)
    obs_daily.rename(columns={'precip_accum_six_hour': 'rain'}, inplace=True)

    # For hourly data, retrieve the data from the database. Only if the database returns an error do we retrieve data
    # from MesoWest.
    try:
        obs_hour = readTimeSeries(config, stid, 'forecast', 'OBS', start_date=start_dt, end_date=end_dt).data
    except MissingDataError:
        if config['debug'] > 9:
            print('verification: missing data in db for hourly obs; retrieving from MesoWest')
        obs_hour = get_obs(config, stid, start, end).data

    # Set DateTime column and round precipitation to avoid trace accumulations
    dateobj = pd.Index(pd.to_datetime(obs_hour[datename])).tz_localize(None) - timedelta(hours=6)
    obs_hour[datename] = dateobj
    obs_hour['RAINHOUR'] = obs_hour['RAINHOUR'].round(2)

    aggregate = {datename: day}
    aggregate['TEMPERATURE'] = {'high': np.max, 'low': np.min}
    aggregate['WINDSPEED'] = {'wind': np.max}
    aggregate['RAINHOUR'] = {'rain': np.sum}

    obs_hour.index = obs_hour['DATETIME']
    obs_hour_day = pd.DataFrame(columns = ['high','low','wind','rain'])
    obs_hour_day['high'] = obs_hour['TEMPERATURE'].resample('1D').max()
    obs_hour_day['low'] = obs_hour['TEMPERATURE'].resample('1D').min()
    obs_hour_day['wind'] = obs_hour['WINDSPEED'].resample('1D').max()
    obs_hour_day['rain'] = obs_hour['RAINHOUR'].resample('1D').sum()

    obs_daily.index = obs_daily['DATETIME']
    obs_daily.drop('DATETIME', axis=1, inplace=True)

    # Compare the daily to hourly values
    obs_daily['high'] = np.fmax(obs_daily['high'], obs_hour_day['high'])
    obs_daily['low'] = np.fmin(obs_daily['low'], obs_hour_day['low'])
    obs_daily['wind'] = np.fmax(obs_daily['wind'], obs_hour_day['wind'])
    obs_daily['rain'] = np.fmax(obs_daily['rain'], obs_hour_day['rain'])

    # Make sure rain has no missing values rather than zeros. Resample appropriately dealt with missing values earlier.
    obs_daily['rain'].fillna(0.0, inplace=True)

    # Round values to nearest degree, knot, and centi-inch
    obs_daily = obs_daily.round({'high': 0, 'low': 0, 'wind': 0, 'rain': 2})

    # Lastly, place all the values we found into a list of Daily objects.
    # Set datetime as the index. This will help use datetime in the creation of the Dailys.
    obs_daily = obs_daily.set_index(datename)
    # Remove extraneous columns
    export_cols = ['high', 'low', 'wind', 'rain']
    for col in obs_daily.columns:
        if col not in export_cols:
            obs_daily.drop(col, axis=1, inplace=True)

    # Create list of Daily objects
    dailys = []
    if config['debug'] > 50:
        print('verification: here are the values')
    for index, row in obs_daily.iterrows():
        date = index.to_pydatetime()
        daily = Daily(stid, date)
        for attr in export_cols:
            setattr(daily, attr, row[attr])
        if config['debug'] > 50:
            print('%s %0.0f/%0.0f/%0.0f/%0.2f' % (daily.date, daily.high, daily.low, daily.wind, daily.rain))
        dailys.append(daily)

    return dailys


def main(config, stid):
    """
    Retrieves the latest verification.
    """
    end_date = datetime.utcnow()

    # Download latest CF6 files. Check the age (or existence) of the current month file.
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    latest_cf6_file = '%s/%s_%s.cli' % (site_directory, stid, end_date.strftime('%Y%m'))
    cache_ok = check_cache_file(config, latest_cf6_file, get_23z=False)
    if not cache_ok:
        # If we're at the beginning of the month, get the last month too
        get_cf6_files(config, stid, 2 if end_date.day < 3 else 1)

    # Get the latest date in the verification. It is likely not complete.
    first_date = get_latest_date(config, 'forecast', stid, 'VERIF')
    if first_date is None:
        first_date = end_date - timedelta(hours=24)
    start_date = datetime(first_date.year, first_date.month, first_date.day, 6)

    # Get the daily verification
    dailys = get_verification(config, stid, start_date, end_date)

    return dailys


def historical(config, stid, start_date):
    """
    Retrieves historical verifications starting at start (datetime). Sets the hour of start to 6, so that we don't get
    incomplete verifications.
    """
    # Get dates
    start_date = start_date.replace(hour=6)
    end_date = datetime.utcnow()

    # Download CF6 files
    get_cf6_files(config, stid, 12)

    # Get the daily verification
    dailys = get_verification(config, stid, start_date, end_date, use_climo=True)

    return dailys
