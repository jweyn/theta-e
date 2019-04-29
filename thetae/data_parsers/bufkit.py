#
# Copyright (c) 2017-18 Jonathan Weyn and Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Module for processing BUFKIT model data.
"""

import os
from datetime import timedelta, datetime
import re
import numpy as np
import pandas as pd
from thetae.util import c_to_f, ms_to_kt, wind_uv_to_speed_dir, mm_to_in
from thetae import Forecast
from io import open


def bufr_delete_yesterday(bufr_dir, stid, date):
    """
    Delete the BUFKIT archived files for a specific date.

    :param bufr_dir: directory where bufrgruven is told to save bufr files
    :param stid:
    :param date: date of files to delete
    :return:
    """
    yesterday_date = (date - timedelta(days=1)).strftime('%Y%m%d')
    os.system('rm -rf %s/bufkit/%s*%s.buf' % (bufr_dir, yesterday_date, stid.lower()))
    os.system('rm -rf %s/gempak/%s*' % (bufr_dir, yesterday_date))
    os.system('rm -rf %s/bufr/*%s*' % (bufr_dir, yesterday_date))
    return


def get_bufkit_forecast(config, bufr, bufkit_dir, model, bufr_name, cycle, stid, forecast_date):
    """
    Produce a Forecast from retrieved bufkit files.
    """
    model_cycle = re.search(r'\d+', cycle).group()
    model_time = '%s%s' % ((forecast_date - timedelta(days=1)).strftime('%Y%m%d'), model_cycle)

    # Specify the correct filenames and account for some odd bufrgruven naming conventions
    bufr_search_model = re.search(r'[^0-2]*', model).group().lower()
    if bufr_search_model == 'fv3':
        bufr_search_model = 'fv3gfsx'
    if bufr_search_model == 'hrrr' and stid.upper()[0] == 'P':
        bufr_search_model = 'hrrrak'
    if bufr_search_model == 'namnest' and stid.upper()[0] == 'P':
        bufr_search_model = 'aknest'
    bufr_file_name = '%s/bufkit/%s.%s_%s.buf' % (bufkit_dir, model_time, bufr_name, stid.lower())

    # Check if bufkit file was already downloaded
    if os.path.isfile(bufr_file_name):
        forecast = bufr_surface_parser(config, model, stid, forecast_date, bufr_file_name)
        return forecast
    else:
        # Call bufrgruven, save files in specified bufr directory
        command = ('%s --dset %s --cycle %s --stations %s --noascii --nozipit --metdat %s --date %s '
                   '--noverbose >& /dev/null' %
                   (bufr, bufr_search_model, model_cycle, stid.lower(), bufkit_dir, model_time[:-2]))
        os.system(command)

        # Check again for bufkit file, if it exists then create forecast object
        if os.path.isfile(bufr_file_name):
            forecast = bufr_surface_parser(config, model, stid, forecast_date, bufr_file_name)
            return forecast

    # If we get here, we're missing the bufkit file
    raise IOError('bufr file %s not found' % bufr_file_name)


def bufr_surface_parser(config, model, stid, forecast_date, bufr_file_name):
    """
    By Luke Madaus. Modified by jweyn and joejoezz.
    Parse surface data from a bufkit file.
    """

    # Open bufkit file
    infile = open(bufr_file_name, 'r', newline='')

    # define variables
    dateTime = []
    temperature = []
    dewpoint = []
    windSpeed = []
    windDirection = []
    rain = []
    pressure = []

    block_lines = []
    inblock = False
    for line in infile:
        if re.search(r'SELV', line):
            try:  # jweyn
                elev = re.search(r'SELV = -?(\d{1,4})', line).groups()[0]  # jweyn: -?
                elev = float(elev)
            except:
                elev = 0.0
        if line.startswith('STN YY'):
            # We've found the line that starts the header info
            inblock = True
            block_lines.append(line)
        elif inblock:
            # Keep appending lines until we start hitting numbers
            if re.search(r'\d{6}', line):
                inblock = False
            else:
                block_lines.append(line)

    # Build an re search pattern based on this
    # We know the first two parts of the section are station id num and date
    re_string = r"(\d{6}|\w{4}) (\d{6})/(\d{4})"
    # Now compute the remaining number of variables
    dum_num = len(block_lines[0].split()) - 2
    for n in range(dum_num):
        re_string = re_string + r" (-?\d{1,4}.\d{2})"
    re_string = re_string + '\r\n'
    for line in block_lines[1:]:
        dum_num = len(line.split())
        for n in range(dum_num):
            re_string = re_string + r'(-?\d{1,4}.\d{2}) '
        re_string = re_string[:-1]  # Get rid of the trailing space
        re_string = re_string + '\r\n'

    # Compile this re_string for more efficient re searches
    block_expr = re.compile(re_string)

    # Now get corresponding indices of the variables we need
    full_line = ''
    for r in block_lines:
        full_line = full_line + r[:-2] + ' '
    # Now split it
    varlist = re.split(r'[ /]', full_line)

    # Now loop through all blocks that match the search pattern we defined above
    blocknum = -1
    infile.seek(0)

    for block_match in block_expr.finditer(infile.read()):
        blocknum += 1
        # Split out the match into each component number
        vals = list(block_match.groups())
        # Check for missing values
        for v in range(len(vals)):
            if vals[v] == -9999.:
                vals[v] = np.nan
        # Set the time
        dt = '20' + vals[varlist.index('YYMMDD')] + vals[varlist.index('HHMM')]
        validtime = datetime.strptime(dt, '%Y%m%d%H%M')

        # End loop if we are more than 60 hours past the start of the forecast date
        if validtime > forecast_date + timedelta(hours=60):
            break

        # Append values at this time step
        dateTime.append(validtime)
        pressure.append(vals[varlist.index('PMSL')])
        temperature.append(c_to_f(vals[varlist.index('T2MS')]))
        dewpoint.append(c_to_f(vals[varlist.index('TD2M')]))
        uwind = ms_to_kt(vals[varlist.index('UWND')])
        vwind = ms_to_kt(vals[varlist.index('VWND')])
        speed, dir = wind_uv_to_speed_dir(uwind, vwind)
        windSpeed.append(speed)
        windDirection.append(dir)
        if 'P01M' in varlist:
            rain.append(mm_to_in(vals[varlist.index('P01M')]))
        else:
            # This condition only applies to FV3 model: save 3 hr precipitation instead of 1 hour
            rain.append(mm_to_in(vals[varlist.index('P03M')]))

    infile.close()

    # first element of rain should be zero (sometimes it is -9999.99)
    rain[0] = '0.0'

    # Make into dataframe
    df = pd.DataFrame({
        'temperature': temperature,
        'dewpoint': dewpoint,
        'windSpeed': windSpeed,
        'windDirection': windDirection,
        'rain': rain,
        'pressure': pressure,
        'dateTime': dateTime
    }, index=dateTime)

    # Convert to forecast object
    forecast_start = forecast_date.replace(hour=6)
    forecast_end = forecast_start + timedelta(days=1)

    # Find forecast start location in timeseries
    try:
        # unlike the mos code, we always use the 'include'
        iloc_start_include = df.index.get_loc(forecast_start)
    except BaseException as e:
        print('bufkit: error getting start time index for %s; check data' % model)
        raise

    # Create forecast object and save timeseries
    forecast = Forecast(stid, model, forecast_date)
    forecast.timeseries.data = df

    # Find forecast end location in time series and save daily values if it exists
    if df.index[-1] >= forecast_end:
        iloc_end = df.index.get_loc(forecast_end)
        high = int(np.round(df.iloc[iloc_start_include:iloc_end]['temperature'].max()))
        low = int(np.round(df.iloc[iloc_start_include:iloc_end]['temperature'].min()))
        max_wind = int(np.round(df.iloc[iloc_start_include:iloc_end]['windSpeed'].max()))
        total_rain = np.sum(df.iloc[iloc_start_include + 1:iloc_end]['rain'])
        forecast.daily.set_values(high, low, max_wind, total_rain)
    else:
        if config['debug'] > 9:
            print('bufkit warning: model %s does not extend to end of forecast period; omitting daily values' % model)

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from bufkit data.
    """
    # Get parameters from the config
    try:
        bufr = config['BUFKIT']['BUFR']
    except KeyError:
        raise KeyError('bufkit: missing BUFR executable path in config BUFKIT options')
    try:
        bufkit_directory = config['BUFKIT']['BUFKIT_directory']
    except KeyError:
        bufkit_directory = '%s/site_data' % config['THETAE_ROOT']
        if config['debug'] > 50:
            print('bufkit warning: setting bufkit file directory to %s' % bufkit_directory)
    try:
        run_time = config['Models'][model]['run_time']
    except KeyError:
        raise KeyError('bufkit: no run_time parameter defined for model %s in config!' % model)
    try:
        bufr_name = config['Models'][model]['bufr_name']
    except KeyError:
        raise KeyError('bufkit: no bufr_name parameter defined for model %s in config!' % model)
    if 'bufr_stid' in config['Stations'][stid]:
        bufr_stid = config['Stations'][stid]['bufr_stid']
    else:
        bufr_stid = str(stid)

    # Delete yesterday's bufkit files
    try:
        if not(config['BUFKIT']['archive']):
            bufr_delete_yesterday(bufkit_directory, bufr_stid, forecast_date - timedelta(days=1))
    except KeyError:
        bufr_delete_yesterday(bufkit_directory, bufr_stid, forecast_date - timedelta(days=1))

    # Get bufkit forecasts
    forecast = get_bufkit_forecast(config, bufr, bufkit_directory, model, bufr_name, run_time, bufr_stid, forecast_date)
    forecast.stid = str(stid)

    return forecast


def historical(config, model, stid, forecast_dates):
    """
    Produce a list of Forecast objects from bufkit for each date in forecast_dates.
    """
    # Get parameters from the config
    try:
        bufr = config['BUFKIT']['BUFR']
    except KeyError:
        raise KeyError('bufkit: missing BUFR executable path in config BUFKIT options')
    try:
        bufkit_directory = config['BUFKIT']['BUFKIT_directory']
    except KeyError:
        bufkit_directory = '%s/site_data' % config['THETAE_ROOT']
        if config['debug'] > 50:
            print('bufkit warning: setting bufkit file directory to %s' % bufkit_directory)
    try:
        run_time = config['Models'][model]['run_time']
    except KeyError:
        raise KeyError('bufkit: no run_time parameter defined for model %s in config!' % model)
    try:
        bufr_name = config['Models'][model]['bufr_name']
    except KeyError:
        raise KeyError('bufkit: no bufr_name parameter defined for model %s in config!' % model)
    if 'bufr_stid' in config['Stations'][stid]:
        bufr_stid = config['Stations'][stid]['bufr_stid']
    else:
        bufr_stid = str(stid)

    forecasts = []
    for forecast_date in forecast_dates:
        try:
            forecast = get_bufkit_forecast(config, bufr, bufkit_directory, model, bufr_name, run_time, bufr_stid,
                                           forecast_date)
            forecast.stid = str(stid)
            forecasts.append(forecast)
        except BaseException as e:
            if int(config['debug']) > 9:
                print('bufkit: failed to retrieve historical forecast for %s on %s' % (model, forecast_date))
                print("*** Reason: '%s'" % str(e))
        # Delete the bufkit files after processing, unless archived
        try:
            if not (config['BUFKIT']['archive']):
                bufr_delete_yesterday(bufkit_directory, bufr_stid, forecast_date)
        except KeyError:
            bufr_delete_yesterday(bufkit_directory, bufr_stid, forecast_date)

    return forecasts
