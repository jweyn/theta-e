#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates timeseries plots for various models.

KNOWN BUGS:
Gray background shading does not account for different wind forecast period
"""

import os
import numpy as np
from pandas import to_datetime
from thetae.db import readForecast, readTimeSeries
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import dates

def plot_timeseries(config, stid, models, forecast_date, variable):
    """
    Timeseries plotting function
    """

    # Initialize plot
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    ax = fig.add_subplot(1, 1, 1)

    # Loop through models to plot
    for model in models:
        try:
            forecast = readForecast(config, stid, model, forecast_date, hour_padding=18)
            forecast = compute_rain_accumulation(forecast, forecast_date)
            data = forecast.timeseries.data[variable]
            ax.plot(to_datetime(forecast.timeseries.data['DATETIME']), data, label=model,
                    color=config['Models'][model]['color'])
        except ValueError:
            print('{} timeseries plot {} failure {}'.format(stid, variable, model))

    # Plot observations
    obs = readTimeSeries(config, stid, 'forecast', 'obs', start_date=forecast_date-timedelta(hours=18),
                         end_date=forecast_date+timedelta(hours=24))
    if variable is not 'RAIN':
        ax.plot(to_datetime(obs.data['DATETIME']), obs.data[variable], label='OBS',
                color='black', linestyle=':', marker='o', ms=4)

    # Plot configurations and saving
    ax.grid()
    ax.set_title('Forecast {} at {}'.format(variable, stid))

    # Legend configuration
    leg = plt.legend(loc=8, ncol=6, mode='expand')
    leg.get_frame().set_alpha(0.5)
    leg_texts = leg.get_texts()
    plt.setp(leg_texts, fontsize='small')

    # x-axis range and label formatting
    ax.set_xlabel('Valid time')
    ax.xaxis.set_major_locator(dates.HourLocator(byhour=[0,3,6,9,12,15,18,21]))
    ax.xaxis.set_major_formatter(dates.DateFormatter('%HZ'))
    ax.xaxis.set_minor_locator(dates.DayLocator())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%h %d'))
    ax.xaxis.set_tick_params(which='minor', pad=15)

    # y-axis range and label formatting
    ax.set_ylabel(variable)
    y_range = plt.ylim()[1]-plt.ylim()[0]
    ax.set_ylim(int(plt.ylim()[0])-y_range*0.10, int(plt.ylim()[1])+y_range*0.05)
    minv, maxv = ax.get_ylim()
    if variable == 'RAIN':
        if maxv > 0.1:
            ax.set_yticks(np.arange(np.round(minv, 1)-0.1, np.round(maxv, 1)+0.2, 0.1))
        else:
            ax.set_yticks(np.arange(np.round(minv, 1) - 0.10, np.round(maxv, 1) + 0.11, 0.01))
    else:
        ax.set_yticks(range(int(minv), int(maxv+1)))

    # Gray out non-forecast times
    plt.axvspan(dates.date2num(forecast_date-timedelta(hours=12)), dates.date2num(forecast_date+timedelta(hours=6)),
                facecolor='0.8', alpha=0.80)
    plt.axvspan(dates.date2num(forecast_date+timedelta(hours=30)), dates.date2num(forecast_date+timedelta(hours=42)),
                facecolor='0.8', alpha=0.80)
    ax.set_xlim(forecast_date-timedelta(hours=12), forecast_date+timedelta(hours=42))

    # Save plot
    save_dir = '%splots/%s/timeseries/' % (config['THETAE_ROOT'], stid)
    plt.savefig('{}/{}_timeseries_{}.png'.format(save_dir, stid, variable), dpi=150)
    return

def compute_rain_accumulation(forecast, forecast_date):
    '''
    Converts a forecast rain timeseries to a cumulative rain timeseries.
    Adjusts so that 0 is the start of the forecast.
    Keeps rain prior to start of forecast as 'negative' rain to show timing uncertainties.
    '''
    cum_rain = np.cumsum(forecast.timeseries.data['RAIN'].fillna(value=0))
    fcst_start_loc = np.where((to_datetime(forecast.timeseries.data['DATETIME']) ==
                               forecast_date+timedelta(hours=6)))[0][0]
    offset = cum_rain[fcst_start_loc]
    cum_rain -= offset
    forecast.timeseries.data['RAIN'] = cum_rain
    return forecast


def main(config, stid, forecast_date):
    """
    Make timeseries plots for a given station.
    """
    # Check for existence of save directories, create if missing
    plot_directory = '%splots/%s' % (config['THETAE_ROOT'],stid)
    if not(os.path.isdir(plot_directory)):
        os.makedirs(plot_directory)
    station_directory = '%splots/%s/timeseries' % (config['THETAE_ROOT'],stid)
    if not(os.path.isdir(station_directory)):
        os.makedirs(station_directory)

    # Get list of models
    models = config['Models'].keys()
    
    # Define variables. Possibly move this to config later
    variables = ['TEMPERATURE', 'DEWPOINT', 'WINDSPEED', 'RAIN']

    # Get forecast
    for variable in variables:
        plot_timeseries(config, stid, models, forecast_date, variable)

    return
