#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve USL forecast data. Unfortunately need to use urlopen to run javascript.

After code by Luke Madaus.
"""

from thetae import Forecast
from thetae.util import wind_dir_to_deg
from datetime import datetime, timedelta
import re
import pandas as pd
import numpy as np
try:
    from urllib.request import urlopen, HTTPError
except ImportError:
    from urllib2 import urlopen, HTTPError

default_model_name = 'USL'


def remove_last_char(value):
    """
    Removes the last character of a string value and converts to float
    """
    try:
        new_value = float(value[:-1])
    except (TypeError, KeyError):
        return np.nan
    return new_value


def check_if_usl_forecast_exists(stid, usl_run_start):
    """
    Checks the parent USL directory to see if USL has run for specified stid and run time.
    Return True if run exists, otherwise return False
    """
    from urllib2 import Request
    model_strtime = usl_run_start.strftime('%Y%m%d_%H')
    webaddr = 'http://www.microclimates.org/forecast/{}/'.format(stid)
    req = Request(webaddr)
    try:
        response = urlopen(req)
    except:
        print('USL page does not exist for {}'.format(stid))
        return False
    page = response.read().decode('utf-8', 'ignore')

    # Look for string of USL run time in the home menu for this station ID (equal to -1 if not found)
    if page.find(model_strtime) != -1:
        return True
    else:
        print('USL has not run yet for {} {}'.format(stid,model_strtime))
        return False


def get_usl_forecast(config, stid, run, forecast_date):

    # Retrieve data
    api_url = 'http://www.microclimates.org/forecast/%s/%s.html'
    run_date = (forecast_date - timedelta(days=1)).replace(hour=int(run))
    get_url = api_url % (stid, datetime.strftime(run_date, '%Y%m%d_%H'))
    try:
        response = urlopen(get_url)
    except HTTPError:
        if config['debug'] > 9:
            print("usl: forecast for %s at run time %s doesn't exist" % (stid, run_date))
        raise
    usl_data = response.read().decode('utf-8')

    # Create a DataFrame
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)
    usl_df = pd.DataFrame(index=pd.date_range(forecast_start, forecast_end, freq='1H'))
    columns = ['temperature', 'dewpoint', 'humidity', 'soilTemperature', 'windDirection', 'windSpeed', 'cloud',
               'netRadiation', 'rain']
    for column in columns:
        usl_df[column] = np.nan

    # Parse the values
    info = usl_data.split('<tr>')
    date_index = 0
    for block in info:
        # Daily values, if that's the appropriate block
        if re.search('&deg;F</td>', block):
            split_block = block.split('<td>')
            try:
                high = int(re.search('(-?\d{1,3})', split_block[1]).groups()[0])
                low = int(re.search('(-?\d{1,3})', split_block[2]).groups()[0])
                max_wind = int(re.search('(\d{1,3})', split_block[3]).groups()[0])
                precip = float(re.search('(\d{1,3}.\d{2})', split_block[4]).groups()[0])
                continue
            except:
                pass
        # Hourly values
        block = re.sub('<th scope="row" class="nobg3">', '', block)
        block = re.sub('<th scope="row" class="nobg">', '', block)
        block = re.sub('</th>', ',', block)
        block = re.sub('</td>', ',', block)
        block = re.sub('</tr>', '', block)
        block = re.sub('<td>', '', block)
        block = re.sub('<td class="hr3">', '', block)
        block = re.sub('\n', '', block)
        if re.search('Time', block):
            continue
        values = block.split(',')[1:-1]  # Omit time and an extra space at the end
        values = [v.strip() for v in values]  # Remove white space
        for v in range(len(values)):  # Convert numbers to float
            try:
                values[v] = float(values[v])
            except (TypeError, ValueError):
                pass
            if values[v] == '':
                values[v] = np.nan
        try:
            usl_df.loc[usl_df.index[date_index], :] = values
            date_index += 1
        except (IndexError, ValueError):
            pass

    # Fix a couple of things
    usl_df['DateTime'] = usl_df.index
    for index in usl_df.index:
        usl_df.loc[index, 'windDirection'] = wind_dir_to_deg(usl_df.loc[index, 'windDirection'])
    usl_df['humidity'] = usl_df['humidity'].apply(remove_last_char)
    usl_df['cloud'] = usl_df['cloud'].apply(remove_last_char)

    # Create Forecast object
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(high, low, max_wind, precip)
    forecast.timeseries.data = usl_df

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from USL.
    """
    # Get the specific run time from the config
    try:
        run_time = config['Models'][model]['run_time'].upper()
    except KeyError:
        run_time = '22Z'
        print('usl warning: no run_time parameter defined for model %s in config; defaulting to 22Z' % model)
    if run_time not in ['12Z', '22Z']:
        print("usl warning: invalid run_time parameter ('%s') given for model %s in config. Should be '12Z' or '22Z'; "
              "defaulting to 22Z" % (run_time, model))
        run_time = '22Z'

    # Check if forecast exists, retrieve if it does exists, otherwise raise error
    usl_run_start = forecast_date-timedelta(days=1)+timedelta(hours=int(run_time[:-1]))
    usl_exists = check_if_usl_forecast_exists(stid, usl_run_start)

    if usl_exists:
        forecast = get_usl_forecast(config, stid, run_time[:-1], forecast_date)
        return forecast
    else:
        raise IOError('usl: forecast for %s at run time %s does not exist' % (stid, run_time))


def historical(config, model, stid, forecast_dates):
    """
    Produce a Forecast object from USL.
    """
    # We don't usually want to do historical for USL. Give a warning.
    print('usl warning: historical forecasts are possible but not recommended unless absolutely necessary.')

    # Get the specific run time from the config
    try:
        run_time = config['Models'][model]['run_time'].upper()
    except KeyError:
        run_time = '22Z'
        print('usl warning: no run_time parameter defined for model %s in config; defaulting to 22Z' % model)
    if run_time not in ['12Z', '22Z']:
        print("usl warning: invalid run_time parameter ('%s') given for model %s in config. Should be '12Z' or '22Z'; "
              "defaulting to 22Z" % (run_time, model))
        run_time = '22Z'

    # Get forecasts
    forecasts = []
    for forecast_date in forecast_dates:
        try:
            usl_run_start = forecast_date - timedelta(days=1) + timedelta(hours=int(run_time[:-1]))
            usl_exists = check_if_usl_forecast_exists(stid, usl_run_start)
            if usl_exists:
                forecast = get_usl_forecast(config, stid, run_time[:-1], forecast_date)
                forecasts.append(forecast)
        except BaseException as e:
            if int(config['debug']) > 9:
                print('usl: failed to retrieve historical forecast for %s' % forecast_date)
                print("*** Reason: '%s'" % str(e))

    return forecasts
