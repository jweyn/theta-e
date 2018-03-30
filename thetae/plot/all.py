#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Service to make all plots specified in config. The main process is used to produce the next day's plots in accordance
with the main engine process. The historical function generates past plots or plots that only need run once.
"""

from datetime import datetime, timedelta
from thetae.util import get_object, config_date_to_datetime, to_bool
from builtins import str


def main(config):
    """
    Main function. Iterates through all plotting scripts specified in config.
    """

    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    forecast_date = (datetime(time_now.year, time_now.month, time_now.day) + timedelta(days=1))
    if config['debug'] > 9:
        print('plot.all: forecast date %s' % forecast_date)

    # Get the plot types from config
    try:
        plot_types = list(config['Plot']['plots'])
    except KeyError:
        print("plot.all warning: no plots specified by key 'plots' in config!")
        return
    # If a config option is given to do plots for all stations, do so
    try:
        plot_all_stations = to_bool(config['Plot']['Options']['plot_all_stations'])
    except:
        plot_all_stations = False
    if plot_all_stations:
        stations = config['Stations'].keys()
    else:
        stations = [config['current_stid']]

    # Do the plots
    for plot_type in plot_types:
        print("plot.all: making '%s' plots" % plot_type)
        for stid in stations:
            if config['debug'] > 50:
                print("plot.all: plotting '%s' for station %s" % (plot_type, stid))
            try:
                # Each plotting script has a function 'main' which makes a plot
                get_object('thetae.plot.%s' % plot_type).main(config, stid, forecast_date)
            except BaseException as e:
                print('plot.all: failed to make plot %s for %s' % (plot_type, stid))
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise
                continue
            

def historical(config, stid):
    """
    Function to produce historical plots, for a specific site. Iterates over plotting functions specified in config
    which have a 'historical' attribute, and begins at the config start_date.
    """

    print('plot.all: generating historical plots for station %s' % stid)

    # Figure out which days we are forecasting for since config start_date.
    time_now = datetime.utcnow()
    forecast_dates = []
    try:
        start_date = config_date_to_datetime(config['Stations'][stid]['start_date'])
    except:
        print('plot.all warning: cannot get start_date in config for station %s, setting to -30 days' % stid)
        start_date = (datetime(time_now.year, time_now.month, time_now.day) - timedelta(days=30))
    date = start_date
    while date < time_now:
        forecast_dates.append(date)
        date = date + timedelta(hours=24)
    if config['debug'] > 9:
        print('plot.all: historical plots starting %s' % start_date)

    # Get the plot types from config
    try:
        plot_types = list(config['Plot']['plots'])
    except KeyError:
        print("plot.all warning: no plots specified by key 'plots' in config!")
        return
    for plot_type in plot_types:
        print("plot.all: making '%s' plots" % plot_type)
        if config['debug'] > 9:
            print("plot.all: making '%s' plot for station %s" % (plot_type, stid))
        try:
            # Each plotting script has a function 'main' which makes a plot
            get_object('thetae.plot.%s' % plot_type).historical(config, stid)
        except AttributeError:
            if config['debug'] > 9:
                print("plot.all: no historical '%s' plot" % plot_type)
        except BaseException as e:
            print('plot.all: failed to make historical plot %s for %s' % (plot_type, stid))
            print("*** Reason: '%s'" % str(e))
            if config['traceback']:
                raise
            continue

    return
