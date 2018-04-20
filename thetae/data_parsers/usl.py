#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve USL forecast data.

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


def remove_last_char(series):
    """
    Returns a series with the last character of a string removed, converted to float
    """
    new_series = series.copy()
    for j in range(len(series)):
        try:
            new_series.iloc[j] = float(series.iloc[j][:-1])
        except (TypeError, KeyError):
            pass
    return new_series


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
        try:
            usl_df.loc[usl_df.index[date_index], :] = values
            date_index += 1
        except (IndexError, ValueError):
            pass

    # Fix a couple of things
    usl_df['DateTime'] = usl_df.index
    for index in usl_df.index:
        usl_df.loc[index, 'windDirection'] = wind_dir_to_deg(usl_df.loc[index, 'windDirection'])
    usl_df['humidity'] = remove_last_char(usl_df['humidity'])
    usl_df['cloud'] = remove_last_char(usl_df['cloud'])

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

    # Get forecast
    forecast = get_usl_forecast(config, stid, run_time[:-1], forecast_date)

    return forecast
