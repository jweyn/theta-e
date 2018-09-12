#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Version history
2016-01-25: Version 1.0
2016-09-13: Version 1.1
    -- Added parameter add_days to add more days to the wind plots, which
       usually have less data
2016-09-14: Version 1.2
    -- Added command-line parser argument for search and variables to plot
    -- Added a separate module file for settings
    -- Added an option for an output directory
    -- A few cosmetic improvements
2016-09-21: Version 1.3
    -- Added an input option make_subdir to decide whether a subdirectory
       named station_id4 is used for image output
2016-11-22: Version 1.4
    -- Added sanity checks to remove extreme temperature and precip data
2017-04-07: Version 1.5
    -- Added try-except catch for missing days

Creates climatology plots of maximum temperature, minimum temperature,
precipitation, and 2-min. wind speed and direction for a given station ID
over a range of historical dates.
"""


from thetae.util import get_ghcn_stid, config_date_to_datetime
import numpy as np
import ulmo
import os
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from .windrose import WindroseAxes


__version__ = '1.5'


def plot_windrose(wdf2, wsf2, start_date=None, end_date=None, start_year=None,
                  stid=None, outdir='.', img_type='svg'):
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    ax = WindroseAxes.from_ax(fig=fig)
    ax.bar(wdf2, wsf2, bins=np.arange(5, 36, 5),
           opening=1.0, nsector=36, edgecolor='white')
    if (start_year is not None and not (start_date is not None and start_date.year < start_year)):
        start_year = start_date.year
    if start_date is not None and end_date is not None and stid is not None:
        ax.set_title('Max 2-min wind rose for ' + stid + ' from ' +
                     datetime.strftime(start_date, "%d %b") + ' to ' +
                     datetime.strftime(end_date, "%d %b") + ' for ' +
                     '{:d} to {:d}\n'.format(start_year, end_date.year))
    box = ax.get_position()
    ax.set_position([box.x0 + 0.1 * box.width, box.y0 - box.height * 0.05, box.width, box.height])
    ax.legend(title='Speed (knots)', loc='center right', bbox_to_anchor=(-.1, 0.5))
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_windrose.%s' % (outdir, stid, img_type), dpi=200)


def plot_histogram(x, facecolor='b', add_mean=False, bins=None, align='left'):
    fig, ax = plt.subplots()
    if bins is None:
        bins = int(np.nanmax(x) - np.nanmin(x))
    n, bins, patches = plt.hist(x, bins=bins, facecolor=facecolor, normed=True, align=align, )
    ylim = ax.get_ylim()
    if ylim[1] - np.nanmax(n) < 0.005:
        ax.set_ylim([ylim[0], ylim[1] + 0.005])
    ax.set_yticklabels(['{:.1f}'.format(100. * l) for l in plt.yticks()[0]])
    ax.set_ylabel('Frequency (%)')
    if add_mean:
        mean = np.mean(x)
        plt.axvline(mean, linewidth=1.5, color='black')
        plt.text(mean + 0.5, 1.02 * np.nanmax(n), 'Mean: {:.1f}'.format(mean))
    return fig, ax, n


def plot_maxt(x, start_date=None, end_date=None, start_year=None, stid=None, outdir='.', img_type='svg'):
    fig, ax, n = plot_histogram(x, facecolor=(0.1, 0.6, 0.4), add_mean=True)
    ax.set_xlabel('Maximum temperature ($^{\circ}$F)')
    if (start_year is not None and not (start_date is not None and start_date.year < start_year)):
        start_year = start_date.year
    if start_date is not None and end_date is not None and stid is not None:
        ax.set_title('Maximum temperature for ' + stid + ' from ' +
                     datetime.strftime(start_date, "%d %b") + ' to ' +
                     datetime.strftime(end_date, "%d %b") + ' for ' +
                     '{:d} to {:d}\n'.format(start_year, end_date.year))
    fig.set_size_inches(8, 6)
    plt.tight_layout()
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_maxt.%s' % (outdir, stid, img_type), dpi=200)


def plot_mint(x, start_date=None, end_date=None, start_year=None, stid=None, outdir='.', img_type='svg'):
    fig, ax, n = plot_histogram(x, facecolor=(0.6, 0.1, 0.4), add_mean=True)
    ax.set_xlabel('Minimum temperature ($^{\circ}$F)')
    if (start_year is not None and not (start_date is not None and start_date.year < start_year)):
        start_year = start_date.year
    if start_date is not None and end_date is not None and stid is not None:
        ax.set_title('Minimum temperature for ' + stid + ' from ' +
                     datetime.strftime(start_date, "%d %b") + ' to ' +
                     datetime.strftime(end_date, "%d %b") + ' for ' +
                     '{:d} to {:d}\n'.format(start_year, end_date.year))
    fig.set_size_inches(8, 6)
    plt.tight_layout()
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_mint.%s' % (outdir, stid, img_type), dpi=200)


def plot_wspeed(x, start_date=None, end_date=None, start_year=None, stid=None, outdir='.', img_type='svg'):
    fig, ax, n = plot_histogram(x, facecolor=(0.2, 0.4, 0.8), add_mean=True)
    ax.set_xlabel('Wind speed (knots)')
    if (start_year is not None and not (start_date is not None and start_date.year < start_year)):
        start_year = start_date.year
    if start_date is not None and end_date is not None and stid is not None:
        ax.set_title('Max 2-min wind speed for ' + stid + ' from ' +
                     datetime.strftime(start_date, "%d %b") + ' to ' +
                     datetime.strftime(end_date, "%d %b") + ' for ' +
                     '{:d} to {:d}\n'.format(start_year, end_date.year))
    fig.set_size_inches(8, 6)
    plt.tight_layout()
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_windsp.%s' % (outdir, stid, img_type), dpi=200)


def plot_precip(x, start_date=None, end_date=None, start_year=None, stid=None, outdir='.', img_type='svg'):
    bins = np.array([0.0, 0.05, 0.10, 0.25, 0.50, 1.0, 2.0, ])
    x1 = np.zeros_like(x)
    for j in range(len(x)):
        for k in range(len(bins) - 1):
            if (x[j] > bins[k]) and (x[j] <= bins[k + 1]):
                x1[j] = k + 1
    x1[x > bins[-1]] = len(bins) + 1
    fig, ax, n = plot_histogram(x1, facecolor=(0.8, 0.7, 0.1), bins=range(len(bins) + 2), align='mid')
    ax.set_xlabel('Precipitation (inches)')
    if (start_year is not None and not (start_date is not None and start_date.year < start_year)):
        start_year = start_date.year
    if start_date is not None and end_date is not None and stid is not None:
        ax.set_title('Daily precipitation for ' + stid + ' from ' +
                     datetime.strftime(start_date, "%d %b") + ' to ' +
                     datetime.strftime(end_date, "%d %b") + ' for ' +
                     '{:d} to {:d}\n'.format(start_year, end_date.year))
    xlabels = ['{:1.2f}'.format(bins[0])]
    for b in range(len(bins) - 1):
        xlabels.append('{:1.2f}-{:1.2f}'.format(bins[b] + 0.01, bins[b + 1]))
    xlabels.append('{:1.2f}+'.format(bins[-1]))
    ax.set_xticklabels(xlabels)
    plt.setp(ax.get_xticklabels(), ha='left')
    fig.set_size_inches(8, 6)
    plt.tight_layout()
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_precip.%s' % (outdir, stid, img_type), dpi=200)
    ax.set_xlim([1, len(bins) + 1])
    ax.set_xticklabels(xlabels[1:])
    ax.set_ylim([0, np.floor(100. * (np.nanmax(n[1:]) + 0.02)) / 100.])
    ax.set_yticklabels(['{:.1f}'.format(100. * l) for l in plt.yticks()[0]])
    if outdir is not None and stid is not None:
        plt.savefig('%s/%s_climo_precipzoomed.%s' % (outdir, stid, img_type), dpi=200)
    plt.show()
    return x1


def main(config, *args):
    if config['debug'] > 50:
        print('plot.climo: nothing to do')

    return


def historical(config, stid):
    """
    Produce plots of climatology for the forecast period of a station.
    """
    # Get parameters from config
    try:
        start_date = config_date_to_datetime(config['Stations'][stid]['forecast_start'])
    except KeyError:
        start_date = datetime.utcnow().date()
        print("plot.climo warning: 'forecast_start' not specified; setting forecast start to %s" % start_date)
    try:
        end_date = config_date_to_datetime(config['Stations'][stid]['forecast_end'])
    except KeyError:
        end_date = start_date + timedelta(days=14)
        print("plot.climo warning: 'forecast_end' not specified; setting forecast end to %s" % end_date)
    try:
        image_type = config['Plot']['Options']['plot_file_format']
    except KeyError:
        image_type = 'svg'
        if config['debug'] > 50:
            print('plot.climo warning: using default image file format (svg)')

    # Get the file directory and attempt to create it if it doesn't exist
    try:
        file_dir = config['Plot']['Options']['output_dir']
    except KeyError:
        file_dir = '%s/site_data' % config['THETAE_ROOT']
        print('plot.climo warning: setting output directory to default')
    os.makedirs(file_dir, exist_ok=True)
    if config['debug'] > 9:
        print('plot.climo: writing output to %s' % file_dir)

    # Get parameters
    start_year = 1900
    end_year = datetime.utcnow().year - 1
    ghcn_stid = get_ghcn_stid(config, stid)

    # Get the data
    if config['debug'] > 0:
        print('plot.climo: fetching data from NCDC')
    vars_used = ['TMAX', 'TMIN', 'WDF2', 'WSF2', 'PRCP']
    data = ulmo.ncdc.ghcn_daily.get_data(ghcn_stid, elements=vars_used, as_dataframe=True)
    D = {}  # data dictionary, makes things easier
    Ds = {}  # date-subset data dictionary
    Dd = {}  # starting date dictionary

    # Copy data from pandas dataframe so we don't change the original
    for v in vars_used:
        D[v] = data[v].copy()
        Ds[v] = []
        # Some variables (often wind) start at a later time than the rest
        Dd[v] = pd.to_datetime(D[v].index[0].to_timestamp())

    # Read the values of the data points as floats, restricting to years specified
    for v in vars_used:
        D[v].value = D[v].value.astype('float')
        D[v] = D[v]['value'][str(start_year):str(end_year)]

    # Create dates list for range of days each year
    dates = []
    wdates = []  # for winds, taking into account add_days
    add_days = 5
    w_start_date = start_date - timedelta(add_days)
    w_end_date = end_date + timedelta(add_days)

    for year in range(start_year, end_year + 1):
        date_start = datetime(year, start_date.month, start_date.day)
        date_end = datetime(year, end_date.month, end_date.day)
        w_date_start = date_start - timedelta(add_days)
        w_date_end = date_end + timedelta(add_days)
        dates += pd.date_range(start=date_start, end=date_end, )
        wdates += pd.date_range(start=w_date_start, end=w_date_end, )

    for v in vars_used:
        if v[0] != 'W':
            for j in range(len(dates)):
                if dates[j] >= Dd[v]:
                    try:
                        Ds[v].append(D[v][dates[j]])
                    except KeyError:
                        pass
        else:
            for j in range(len(wdates)):
                if wdates[j] >= Dd[v]:
                    try:
                        Ds[v].append(D[v][wdates[j]])
                    except:
                        pass

    for v in vars_used:
        Ds[v] = np.array(Ds[v])

    # Correct data units for WxChallenge. Temperature from 10ths of C to F; wind
    # speed from 10ths of m/s to knots; precipitation from 10ths of mm to in.
    # Also remove missing data.
    Ds['TMAX'] = Ds['TMAX'] / 10. * 9. / 5. + 32.
    Ds['TMIN'] = Ds['TMIN'] / 10. * 9. / 5. + 32.
    Ds['WSF2'] = Ds['WSF2'] / 10. * 1.94384
    Ds['PRCP'] = np.floor(Ds['PRCP'] / 2.54) / 100.

    # Sanity checks: remove data that seems far extreme
    min_bound = {'TM': -100., 'PR': 0.}
    max_bound = {'TM': 140., 'PR': 50.}
    for v in vars_used:
        try:
            Ds[v][Ds[v] < min_bound[v[:2]]] = np.nan
            Ds[v][Ds[v] > max_bound[v[:2]]] = np.nan
        except KeyError:
            pass

    # Remove missing values for analysis
    for v in vars_used:
        Ds[v] = Ds[v][~np.isnan(Ds[v])]

    # Create another dictionary with rounded values to fix for unit corrections
    Dr = {}
    for v in vars_used:
        Dr[v] = np.round(Ds[v])

    Dr['PRCP'] = 1.0 * Ds['PRCP']

    # %% Plotting section
    if config['debug'] > 9:
        print('plot.climo: writing output to %s' % file_dir)
    plot_windrose(Ds['WDF2'], Dr['WSF2'], start_date=w_start_date, end_date=w_end_date,
                  start_year=Dd['WSF2'].year, stid=stid, outdir=file_dir, img_type=image_type)
    plot_wspeed(Dr['WSF2'], start_date=w_start_date, end_date=w_end_date,
                start_year=Dd['WSF2'].year, stid=stid, outdir=file_dir, img_type=image_type)
    plot_maxt(Dr['TMAX'], start_date=start_date, end_date=end_date,
              start_year=Dd['TMAX'].year, stid=stid, outdir=file_dir, img_type=image_type)
    plot_mint(Dr['TMIN'], start_date=start_date, end_date=end_date,
              start_year=Dd['TMIN'].year, stid=stid, outdir=file_dir, img_type=image_type)
    n = plot_precip(Dr['PRCP'], start_date=start_date, end_date=end_date,
                    start_year=Dd['PRCP'].year, stid=stid, outdir=file_dir, img_type=image_type)

    return
