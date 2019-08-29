#
# Copyright (c) 2019 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates customizable hi/lo and verification plots
"""

import os
import numpy as np
import pandas as pd
from thetae.db import readDaily
from datetime import timedelta
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt


def plot_hilo(config, stid, models, forecast_date, plot_directory, image_type, no_bias=False, verify_lines=False,
              sort_by='high', title_text=None):
    """
    Make bar plots of high and low temperature

    :param no_bias: use bias-corrected values
    :param verify_lines: draw lines with verification of high/low
    :param sort_by: sort skill scores by 'high' or 'low' temperature (default: high)
    :param title_text: (optional): Extra text to be added to title to distinguish verification plots
    """

    # DataFrame of forecasts, bias, and skill to fill
    df = pd.DataFrame(index=models, columns=['hi', 'lo', 'hi_bias', 'lo_bias', 'hi_skill_persist', 'hi_skill_climo',
                                             'lo_skill_persist', 'lo_skill_climo', 'hi_skill_avg', 'lo_skill_avg',
                                             'num_days', 'color'])

    # load model stats json into dataframe
    json_stats = pd.read_json('%s/archive/theta-e-stats.json' % config['THETAE_ROOT'])
    for model in models:
        # this check allows models with no verification (i.e. first day of a new model) to be plotted
        if model in json_stats.index:
            if no_bias:
                df['hi_skill_persist'][model] = json_stats.loc[model][stid]['stats']['high']['skillPersistNoBias']
                df['lo_skill_persist'][model] = json_stats.loc[model][stid]['stats']['low']['skillPersistNoBias']
                df['hi_skill_climo'][model] = json_stats.loc[model][stid]['stats']['high']['skillClimoNoBias']
                df['lo_skill_climo'][model] = json_stats.loc[model][stid]['stats']['low']['skillClimoNoBias']
            else:
                df['hi_skill_persist'][model] = json_stats.loc[model][stid]['stats']['high']['skillPersist']
                df['lo_skill_persist'][model] = json_stats.loc[model][stid]['stats']['low']['skillPersist']
                df['hi_skill_climo'][model] = json_stats.loc[model][stid]['stats']['high']['skillClimo']
                df['lo_skill_climo'][model] = json_stats.loc[model][stid]['stats']['low']['skillClimo']
            df['num_days'][model] = json_stats.loc[model][stid]['attrs']['numDays']
            df['hi_bias'][model] = json_stats.loc[model][stid]['stats']['high']['bias']
            df['lo_bias'][model] = json_stats.loc[model][stid]['stats']['low']['bias']
        else:
            df['num_days'][model] = 0.0
        df['color'][model] = config['Models'][model]['color']

    # change None to NaN
    df.fillna(value=np.nan, inplace=True)

    # retrieve a list of daily forecast objects
    forecasts = readDaily(config, stid, 'forecast', 'daily_forecast', start_date=forecast_date, end_date=forecast_date,
                          force_list=True)

    # calculate bias-corrected forecasts
    for forecast in forecasts:
        model = forecast.model
        if no_bias:
            df.loc[model, 'hi'] = np.round(forecast.high + df['hi_bias'][model], 0)
            df.loc[model, 'lo'] = np.round(forecast.low + df['lo_bias'][model], 0)
        else:
            df.loc[model, 'hi'] = np.round(forecast.high, 0)
            df.loc[model, 'lo'] = np.round(forecast.low, 0)

    # compute average skill
    df['hi_skill_avg'] = np.mean([df['hi_skill_persist'], df['hi_skill_climo']], axis=0)
    df['lo_skill_avg'] = np.mean([df['lo_skill_persist'], df['lo_skill_climo']], axis=0)
    df['hi_skill_avg'] = np.mean([df['hi_skill_persist'], df['hi_skill_climo']], axis=0)
    df['lo_skill_avg'] = np.mean([df['lo_skill_persist'], df['lo_skill_climo']], axis=0)

    # drop models with missing values (set threshold so if only skill scores are missing the model is still plotted)
    df.dropna(how='any', thresh=4, inplace=True)

    # sort models by average of climo and persist skill scores
    if sort_by == 'high':
        df.sort_values(by='hi_skill_avg', ascending=False, inplace=True)
    elif sort_by == 'low':
        df.sort_values(by='lo_skill_avg', ascending=False, inplace=True)
    else:
        raise ValueError('daily.plot_hilo error: invalid sort_by value specified, must be "high" or "low"')

    # make skill scores a minimum of -0.5
    df['hi_skill_persist'] = df['hi_skill_persist'].clip(lower=-0.5)
    df['hi_skill_climo'] = df['hi_skill_climo'].clip(lower=-0.5)
    df['lo_skill_persist'] = df['lo_skill_persist'].clip(lower=-0.5)
    df['lo_skill_climo'] = df['lo_skill_climo'].clip(lower=-0.5)

    # Initialize plot
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    gs = matplotlib.gridspec.GridSpec(3, 1)

    # top panel is the bar plot
    ax1 = plt.subplot(gs[:-1,:])
    plt.bar(range(len(df.index)), df['hi']-df['lo'], bottom=df['lo'], color=df['color'].values,
            edgecolor=df['color'].values, align='center')

    # plot verify lines if applicable, make sure y-lims account for verification
    if verify_lines is not False:
        # load verification
        obs = readDaily(config, stid, 'forecast', 'verif', start_date=forecast_date, end_date=forecast_date)
        plt.axhline(y=obs.high, lw=3, c='k')
        plt.axhline(y=obs.high, lw=2, c='r')
        plt.axhline(y=obs.low, lw=3, c='k')
        plt.axhline(y=obs.low, lw=2, c='b')
        ax1.set_ylim((np.min(np.hstack((df['lo'].values.astype('float'), obs.low))) - 4,
                              np.max(np.hstack((df['hi'].values.astype('float'), obs.high)))+4))
    else:
        ax1.set_ylim((np.min(df['lo']) - 4, np.max(df['hi']) + 4))
    ax1.set_xlim((-1.0, len(df.index)))

    #add labels to plot
    for i in range(0, len(df.index)):
        # model fontsize is be dynamic based on how far apart the high and low are and how many models there are
        if 5.0 < df['hi'][i]-df['lo'][i] < 15.0:
            model_fontsize = 6
        elif df['hi'][i]-df['lo'][i] < 5.0:
            model_fontsize = 0
        else:
            if len(df.index) < 20:
                model_fontsize = 10
            else:
                model_fontsize = 6
        plt.text(i, 0.5 * (df['hi'][i]+df['lo'][i]), df.index[i], color='k', fontsize=model_fontsize,
                 horizontalalignment='center', verticalalignment='center', rotation=90)
        plt.text(i, df['hi'][i] + 0.25, str(int(df['hi'][i])), color='k', fontsize=12, horizontalalignment='center',
                 verticalalignment='bottom')
        plt.text(i, df['lo'][i] - 0.25, str(int(df['lo'][i])), color='k', fontsize=12, horizontalalignment='center',
                 verticalalignment='top')

    # set ticks, no x-labels on this plot
    ax1.set_xticks(range(len(df.index)))
    ax1.set_xticklabels(['']*len(df.index))

    # plot labels
    plt.ylabel('Temperature (F)')
    if no_bias:
        plt.title('Bias-Corrected Forecast High/Low at {} for {}'.format(stid, forecast_date.strftime('%d-%b %Y')))
        nobias_txt = '_nobias'
    else:
        plt.title('Forecast High/Low at {} for {}'.format(stid, forecast_date.strftime('%d-%b %Y')))
        nobias_txt = ''

    # skill score panel
    ax2 = plt.subplot(gs[-1, :])
    ax2.text(0.005, 1.045, '# verif. days:', ha='left', va='center', fontsize=7, transform=ax2.transAxes)
    width = 0.35
    halfwidth = width/2.
    # Highlight the background and plot number of days that verification was run for
    for i, model in enumerate(df.index):
        ax2.axvspan(i-width, i+width, facecolor=df['color'].values[i],alpha=0.2)
        ax2.annotate(df['num_days'][i].astype('int'), (i, 0.930), ha='center', va='center', color='k', fontsize=8)
    ind = np.arange(len(df.index))
    ax2.bar(ind-width, df['hi_skill_climo'], color='r', edgecolor='r', width=halfwidth, label='High Climo')
    ax2.bar(ind-halfwidth, df['hi_skill_persist'], color='r', edgecolor='r', alpha=0.4, width=halfwidth,
            label='High Persist')
    ax2.bar(ind, df['lo_skill_climo'], color='b', edgecolor='b', width=halfwidth, label='Low Climo')
    ax2.bar(ind+halfwidth, df['lo_skill_persist'], color='b', edgecolor='b', alpha=0.4, width=halfwidth,
            label='Low Persist')

    # Format axes
    ax2.set_ylabel('Skill Score')
    ax2.set_title('<--best        Skill relative to Climatology/Persistence        worst-->', fontsize=10)
    ax2.set_xticks(ind)
    ax2.set_xticklabels(df.index, rotation=90)
    ax2.legend(loc=4, ncol=2, prop={'size': 7})
    ax2.set_ylim((-0.5, 1.0))
    ax2.set_xlim((-1.0, len(df.index)))
    ax2.axhline(y=0, linewidth=2, c='k')
    # Change label size
    for tick in ax2.xaxis.get_major_ticks():
        tick.label.set_fontsize(8)

    if title_text is not None:
        plt.savefig('{}/{}_hilo_{}skill{}_{}.{}'.format(plot_directory, stid, sort_by, nobias_txt, title_text,
                                                        image_type), dpi=150, bbox_inches='tight')
    else:
        plt.savefig('{}/{}_hilo_{}skill{}.{}'.format(plot_directory, stid, sort_by, nobias_txt, image_type), dpi=150,
                    bbox_inches='tight')

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

    # tomorrow sort by high
    plot_hilo(config, stid, models, forecast_date, plot_directory, image_type, sort_by='high')
    # tomorrow NO BIAS sort by high
    plot_hilo(config, stid, models, forecast_date, plot_directory, image_type, no_bias=True, sort_by='high')
    # tomorrow sort by low
    plot_hilo(config, stid, models, forecast_date, plot_directory, image_type, sort_by='low')
    # tomorrow NO BIAS sort by low
    plot_hilo(config, stid, models, forecast_date, plot_directory, image_type, no_bias=True, sort_by='low')
    # today so far
    plot_hilo(config, stid, models, forecast_date-timedelta(days=1),
              plot_directory, image_type, sort_by='high', verify_lines=True, title_text='today')
    # yesterday
    plot_hilo(config, stid, models, forecast_date-timedelta(days=2),
              plot_directory, image_type, sort_by='high', verify_lines=True, title_text='yesterday')
    # 2 days ago
    plot_hilo(config, stid, models, forecast_date-timedelta(days=3),
              plot_directory, image_type, sort_by='high', verify_lines=True, title_text='2daysago')
    return

