#
# Copyright (c) 2019 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates hi/lo and verification plots for tomorrow, current day, and yesterday
"""

import os
import numpy as np
import pandas as pd
from thetae.db import readDaily
from thetae.util import date_to_datetime
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib import dates

import pdb

def plot_hilo(config, stid, models, forecast_date, plot_directory, image_type):

    # DataFrame of forecasts, and skill to fill
    df = pd.DataFrame(index=models, columns=['hi', 'lo', 'hi_skill_persist', 'hi_skill_climo', 'lo_skill_persist',
                                             'lo_skill_climo', 'num_days'])
    # Same dataframe but for bias-corrected forecasts
    df_nobias = pd.DataFrame(index=models, columns=['hi', 'lo', 'hi_skill_persist', 'hi_skill_climo',
                                                    'lo_skill_persist', 'lo_skill_climo', 'num_days'])
    # load model stats into dataframe (just a way of loading the OrderedDict)
    df_stats = pd.read_json('%s/archive/theta-e-stats.json' % config['THETAE_ROOT'])

    # retrieve a list of daily forecast objects
    forecasts = readDaily(config, stid, 'forecast', 'daily_forecast', start_date=forecast_date, force_list=True)

    # load model forecasts and stats into dataframes
    for forecast in forecasts:
        model = forecast.model
        df['hi'][model] = np.round(forecast.high, 0)
        df['lo'][model] = np.round(forecast.low, 0)
        if model in df_stats.index:
            df['hi_skill_persist'][model] = df_stats.loc[model][stid]['stats']['high']['skillPersist']
            df['lo_skill_persist'][model] = df_stats.loc[model][stid]['stats']['low']['skillPersist']
            df['hi_skill_climo'][model] = df_stats.loc[model][stid]['stats']['high']['skillClimo']
            df['lo_skill_climo'][model] = df_stats.loc[model][stid]['stats']['low']['skillClimo']
            df['num_days'][model] = df_stats.loc['ACCUWX']['KYKM']['attrs']['numDays']

            if 'bias' in df_stats.loc[model][stid]['stats']['high'] and \
                    df_stats.loc[model][stid]['stats']['high']['bias'] is not None:
                df_nobias['hi'][model] = np.round(df['hi'][model] + df_stats.loc[model][stid]['stats']['high']['bias'],
                                                  0)
                df_nobias['lo'][model] = np.round(df['lo'][model] + df_stats.loc[model][stid]['stats']['low']['bias'],
                                                  0)
                df_nobias['hi_skill_persist'][model] = df_stats.loc[model][stid]['stats']['high']['skillPersistNoBias']
                df_nobias['lo_skill_persist'][model] = df_stats.loc[model][stid]['stats']['low']['skillPersistNoBias']
                df_nobias['hi_skill_climo'][model] = df_stats.loc[model][stid]['stats']['high']['skillClimoNoBias']
                df_nobias['lo_skill_climo'][model] = df_stats.loc[model][stid]['stats']['low']['skillClimoNoBias']
                df_nobias['num_days'][model] = df_stats.loc['ACCUWX']['KYKM']['attrs']['numDays']

    pdb.set_trace()
    # drop models with all missing values
    df.dropna(how='all', inplace=True)
    df_nobias.dropna(how='all', inplace=True)




    pdb.set_trace()
    return


def main(config, stid, forecast_date):
    """
    Make hilo plots for a given station.
    """
    # Get the file directory and attempt to create it if it doesn't exist
    try:
        plot_directory = config['Plot']['Options']['plot_directory']
    except KeyError:
        plot_directory = '%s/site_data' % config['THETAE_ROOT']
        print('plot.hilo warning: setting output directory to default')
    if not (os.path.isdir(plot_directory)):
        os.makedirs(plot_directory)
    if config['debug'] > 9:
        print('plot.hilo: writing output to %s' % plot_directory)
    try:
        image_type = config['Plot']['Options']['plot_file_format']
    except KeyError:
        image_type = 'svg'
        if config['debug'] > 50:
            print('plot.hilo warning: using default image file format (svg)')

    # Get list of models
    models = list(config['Models'].keys())

    if config['debug'] > 50:
        print('plot.hilo: plotting Hi-Lo bar plots')
    plot_hilo(config, stid, models, forecast_date, plot_directory, image_type)

    return