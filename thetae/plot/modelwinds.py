#
# Copyright (c) 2019 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates model plots related to model forecast winds
1. Model wind direction comparison
2. Mixed layer wind timeseries
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from thetae.db import readForecast, readTimeSeries
from thetae.util import wind_speed_dir_to_uv
from thetae import MissingDataError
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib import dates


def plot_model_winds(config, stid, models, forecast_date, plot_directory, image_type):
    """
    model wind barbs plotting function
    """

    # Initialize plot
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    ax = fig.add_subplot(1, 1, 1)

    # List of models with good data
    model_list = []

    # Loop through models to plot, "key" variable denotes where to plot on y-axis
    key = 0
    for i, model in enumerate(models):
        try:
            forecast = readForecast(config, stid, model, forecast_date, hour_padding=18)
        except MissingDataError:
            if config['debug'] > 9:
                print('plot.timeseries warning: no hourly data for %s, %s' % (stid, model))
            continue

        times = forecast.timeseries.data['DATETIME']
        wspd = forecast.timeseries.data['WINDSPEED']
        drct = forecast.timeseries.data['WINDDIRECTION']
        uwnd, vwnd = wind_speed_dir_to_uv(wspd.values, drct.values)

        try:
            color = config['Models'][model]['color']
        except KeyError:
            color = 'k'

        plot_times = [dates.date2num(d) for d in pd.to_datetime(times.values)]
        plt.barbs(plot_times, [key]*len(times), uwnd, vwnd, barbcolor=color, flagcolor=color, zorder=2,
                  length=70./(len(models) + 2), lw=0.9)
        key += 1
        model_list.append(model)

    # Plot configurations and saving
    ax.grid()
    ax.set_title('Forecast wind barbs at {}'.format(stid))

    # x-axis range and label formatting
    ax.set_xlabel('Valid time')
    ax.xaxis.set_major_locator(dates.HourLocator(byhour=list(range(0, 25, 3))))
    ax.xaxis.set_major_formatter(dates.DateFormatter('%HZ'))
    ax.xaxis.set_minor_locator(dates.DayLocator())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%h %d'))
    ax.xaxis.set_tick_params(which='minor', pad=15)

    # y-axis range and label formatting
    ax.set_ylabel('Model')
    plt.yticks(range(0,key), model_list)
    plt.ylim((-0.75, len(model_list) - 0.25))

    # Gray out non-forecast times
    plt.axvspan(dates.date2num(forecast_date-timedelta(hours=12)), dates.date2num(forecast_date+timedelta(hours=6)),
                facecolor='0.8', alpha=0.80, zorder=1)
    plt.axvspan(dates.date2num(forecast_date+timedelta(hours=30)), dates.date2num(forecast_date+timedelta(hours=42)),
                facecolor='0.8', alpha=0.80, zorder=1)
    ax.set_xlim(forecast_date-timedelta(hours=12), forecast_date+timedelta(hours=42))

    plt.savefig('{}/{}_WINDBARBS.{}'.format(plot_directory, stid, image_type), bbox_inches="tight", dpi=150)
    return


def plot_mixed_layer_winds(config, stid, models, forecast_date, plot_directory, image_type):
    """
    model mixed-layer winds plotting function
    depends on bufkit functions from plot.timeheight
    """

    from thetae.plot.timeheight import bufr_timeheight_parser, compute_bl_winds

    # Initialize plot
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    ax = fig.add_subplot(1, 1, 1)

    # Make plots for models that have a bufkit file
    for model in models:
        if 'bufr_name' in config['Models'][model].keys():
            try:
                df = bufr_timeheight_parser(config, model, stid, forecast_date)
                bl_df = compute_bl_winds(df)
            except IOError:
                if config['debug'] > 50:
                    print('plot.modelwinds: bufkit import error for %s' % model)
                continue
            try:
                color = config['Models'][model]['color']
            except KeyError:
                color = 'k'

            ax.plot(bl_df.index, bl_df['mean_wind'], color=color, label='%s meanML' % model, zorder=2)
            ax.plot(bl_df.index, bl_df['max_wind'], color=color, label='%s maxML' % model, linestyle='dashed',
                    zorder=2)

    # plot observations (both wind speed and gust)
    try:
        obs = readTimeSeries(config, stid, 'forecast', 'obs', start_date=forecast_date-timedelta(hours=25),
                             end_date=forecast_date+timedelta(hours=24))
        ax.plot(pd.to_datetime(obs.data['DATETIME']), obs.data['WINDSPEED'], label='OBS speed', color='black',
                linestyle=':', marker='o', ms=4)
        ax.plot(pd.to_datetime(obs.data['DATETIME']), obs.data['WINDGUST'].values, label='OBS gust', color='black',
                linestyle='None', marker='x', ms=5)
    except MissingDataError:
        if config['debug'] > 9:
            print('plot.timeseries warning: no data found for observations at %s' % stid)

    # Plot configurations and saving
    ax.grid()
    ax.set_title('Forecast mixed-layer winds at {}'.format(stid))

    # Legend configuration
    leg = plt.legend(loc=9, ncol=4, mode='expand')
    if leg is not None:
        leg.get_frame().set_alpha(0.5)
        leg_texts = leg.get_texts()
        plt.setp(leg_texts, fontsize='x-small')

    # x-axis range and label formatting
    ax.set_xlabel('Valid time')
    ax.xaxis.set_major_locator(dates.HourLocator(byhour=list(range(0, 25, 3))))
    ax.xaxis.set_major_formatter(dates.DateFormatter('%HZ'))
    ax.xaxis.set_minor_locator(dates.DayLocator())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%h %d'))
    ax.xaxis.set_tick_params(which='minor', pad=15)

    # y-axis range and label formatting
    ax.set_ylabel('Wind speed (kt)')
    y_range = plt.ylim()[1]-plt.ylim()[0]
    ax.set_ylim(0, int(plt.ylim()[1]+y_range*0.20))

    # Gray out non-forecast times
    plt.axvspan(dates.date2num(forecast_date-timedelta(hours=12)), dates.date2num(forecast_date+timedelta(hours=6)),
                facecolor='0.8', alpha=0.80, zorder=1)
    plt.axvspan(dates.date2num(forecast_date+timedelta(hours=30)), dates.date2num(forecast_date+timedelta(hours=42)),
                facecolor='0.8', alpha=0.80, zorder=1)
    ax.set_xlim(forecast_date-timedelta(hours=12), forecast_date+timedelta(hours=42))

    plt.savefig('{}/{}_MIXEDLAYERWINDS.{}'.format(plot_directory, stid, image_type), dpi=150)
    return


def main(config, stid, forecast_date):
    """
    Make model winds plots for a given station.
    """
    # Use the previous date if we're not at 6Z yet
    if datetime.utcnow().hour < 6:
        forecast_date -= timedelta(days=1)

    # Get the file directory and attempt to create it if it doesn't exist
    try:
        plot_directory = config['Plot']['Options']['plot_directory']
    except KeyError:
        plot_directory = '%s/site_data' % config['THETAE_ROOT']
        print('plot.modelwinds warning: setting output directory to default')
    if not (os.path.isdir(plot_directory)):
        os.makedirs(plot_directory)
    if config['debug'] > 9:
        print('plot.modelwinds: writing output to %s' % plot_directory)
    try:
        image_type = config['Plot']['Options']['plot_file_format']
    except KeyError:
        image_type = 'svg'
        if config['debug'] > 50:
            print('plot.modelwinds warning: using default image file format (svg)')

    # Get list of models
    models = list(config['Models'].keys())

    # Mixed layer wind plot
    plot_mixed_layer_winds(config, stid, models, forecast_date, plot_directory, image_type)

    # Wind barb model comparison plot
    plot_model_winds(config, stid, models, forecast_date, plot_directory, image_type)
    return
