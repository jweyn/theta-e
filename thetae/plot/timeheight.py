#
# Copyright (c) 2019 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates bufit timeheight plots for various models.

"""

import os
from collections import OrderedDict
import re
import numpy as np
from scipy import interpolate
import pandas as pd
from thetae.db import readForecast, readTimeSeries
from thetae.util import date_to_datetime
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib import dates
import pdb

def plot_timeheight(config, stid, model, forecast_date, variable, profile, plot_dir, img_type):
    """
    Timeseries plotting function
    """

    # stuff that I might need...
    #var_names = ['temperature', 'dewPointDep', 'cloud', 'windSpeed', 'omega']
    variable = variable.upper()
    bufr_vars = ['TMPC', 'DWPC', 'UWND', 'VWND', 'HGHT', 'OMEG', 'CFRL']

    # Get surface pressure from forecast timeseries
    try:
        obs = readTimeSeries(config, stid, 'forecast', 'hourly_forecast', model=model, start_date=profile.keys()[0],
                             end_date=profile.keys()[-1])
    except ValueError:
        if config['debug'] > 9:
            print('plot.timeheight warning: no hourly timeseries data for %s, %s' % (stid, model))

    datetimes = obs.data['DATETIME']
    pressure = obs.data['PRESSURE']







    pdb.set_trace()


    pdb.set_trace()
    return


def bufr_timeheight_parser(config, model, stid, forecast_date):
    """
    Original code by Luke Madaus, modified by Joe Zagrodnik and Jonathan Weyn

    Grab all variables, put in pandas dataframes

    """
    # Load bufkit file
    bufkit_dir = config['BUFKIT']['BUFKIT_directory']
    model_run_hour = config['Models'][model]['run_time'].replace('Z', '')
    bufr_name = config['Models'][model]['bufr_name']
    model_date = (forecast_date-timedelta(days=1)).strftime('%Y%m%d')
    file_name = '%s/bufkit/%s%s.%s_%s.buf' % (bufkit_dir, model_date, model_run_hour, bufr_name, stid.lower())
    try:
        infile = open(file_name, 'r')
    except IOError:
        print('plot.timeheight: missing bufkit file %s' % file_name)

    profile = OrderedDict()

    # Find the block that contains the description of
    # what everything is (header information)
    block_lines = []
    inblock = False
    block_found = False
    for line in infile:
        if line.startswith('PRES TMPC') and not block_found:
            # We've found the line that starts the header info
            inblock = True
            block_lines.append(line)
        elif inblock:
            # Keep appending lines until we start hitting numbers
            if re.match('^\d{3}|^\d{4}', line):
                inblock = False
                block_found = True
            else:
                block_lines.append(line)

    # Now compute the remaining number of variables
    re_string = ''
    for line in block_lines:
        dum_num = len(line.split())
        for n in range(dum_num):
            re_string = re_string + '(-?\d{1,5}.\d{2}) '
        re_string = re_string[:-1]  # Get rid of the trailing space
        re_string = re_string + '\r\n'

    # Compile this re_string for more efficient re searches
    block_expr = re.compile(re_string)

    # Now get corresponding indices of the variables we need
    full_line = ''
    for r in block_lines:
        full_line = full_line + r[:-2] + ' '
    # Now split it
    varlist = re.split('[ /]', full_line)
    # Get rid of trailing space
    varlist = varlist[:-1]

    # Variables we want
    vars_desired = ['TMPC', 'DWPC', 'UWND', 'VWND', 'HGHT', 'OMEG', 'CFRL']

    # Pressure levels to interpolate to
    interp_res = 5
    plevs = range(200,1050,interp_res)

    # We now need to break everything up into a chunk for each
    # forecast date and time
    with open(file_name) as infile:
        blocks = infile.read().split('STID')
        for block in blocks:
            interp_plevs = []
            header = block
            if header.split()[0] != '=':
                continue
            fcst_time = re.search('TIME = (\d{6}/\d{4})', header).groups()[0]
            fcst_dt = datetime.strptime(fcst_time, '%y%m%d/%H%M')

            # End loop if we are more than 60 hours past the start of the forecast date
            if fcst_dt > forecast_date + timedelta(hours=60):
                break
            temp_vars = OrderedDict()
            for var in varlist:
                temp_vars[var] = []
            temp_vars['PRES'] = []
            for block_match in block_expr.finditer(block):
                vals = block_match.groups()
                for val, name in zip(vals, varlist):
                    if float(val) == -9999.:
                        temp_vars[name].append(np.nan)
                    else:
                        temp_vars[name].append(float(val))

            # Unfortunately, bufkit values aren't always uniformly distributed.
            final_vars = OrderedDict()
            cur_plevs = temp_vars['PRES']
            cur_plevs.reverse()
            for var in varlist[1:]:
                if var in (vars_desired + ['SKNT', 'DRCT']):
                    values = temp_vars[var]
                    values.reverse()
                    interp_plevs = list(plevs)
                    num_plevs = len(interp_plevs)
                    f = interpolate.interp1d(cur_plevs, values, bounds_error=False)
                    interp_vals = f(interp_plevs)
                    interp_array = np.full((len(plevs)), np.nan)
                    # Array almost certainly missing values at high pressures
                    interp_array[:num_plevs] = interp_vals
                    interp_vals = list(interp_array)
                    interp_plevs = list(plevs)  # use original array
                    interp_vals.reverse()
                    interp_plevs.reverse()
                    if var == 'SKNT':
                        wspd = np.array(interp_vals)
                    if var == 'DRCT':
                        wdir = np.array(interp_vals)
                if var in vars_desired:
                    final_vars[var] = interp_vals
            final_vars['PRES'] = interp_plevs
            if 'UWND' not in final_vars.keys():
                final_vars['UWND'] = list(wspd * np.sin(wdir * np.pi/180. - np.pi))
            if 'VWND' not in final_vars.keys():
                final_vars['VWND'] = list(wspd * np.cos(wdir * np.pi/180. - np.pi))
            profile[fcst_dt] = final_vars

    return profile


def main(config, stid, forecast_date):
    """
    Make timeseries plots for a given station.
    """
    # Get the file directory and attempt to create it if it doesn't exist
    try:
        plot_directory = config['Plot']['Options']['plot_directory']
    except KeyError:
        plot_directory = '%s/site_data' % config['THETAE_ROOT']
        print('plot.timeseries warning: setting output directory to default')
    if not (os.path.isdir(plot_directory)):
        os.makedirs(plot_directory)
    if config['debug'] > 9:
        print('plot.timeheight: writing output to %s' % plot_directory)
    try:
        image_type = config['Plot']['Options']['plot_file_format']
    except KeyError:
        image_type = 'svg'
        if config['debug'] > 50:
            print('plot.timeseries warning: using default image file format (svg)')

    # Get list of models
    models = list(config['Models'].keys())

    # List of time-height variables
    variables = ['temperature', 'dewPointDep', 'cloud', 'windSpeed', 'omega']

    # Make plots for models that have a bufkit file
    for model in models:
        if 'bufr_name' in config['Models'][model].keys():
            profile = bufr_timeheight_parser(config, model, stid, forecast_date)
            for variable in variables:
                if config['debug'] > 50:
                    print('plot.timeheight: plotting %s for %s' % (variable,model))
                plot_timeheight(config, stid, model, forecast_date, variable, profile, plot_directory, image_type)
    return