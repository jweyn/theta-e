#
# Copyright (c) 2019 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Generates bufkit timeheight plots for various models.
"""

import os
from collections import OrderedDict
import re
import numpy as np
from scipy import interpolate
import pandas as pd
from scipy.ndimage.filters import gaussian_filter
from math import ceil
from datetime import datetime, timedelta
from io import open
import matplotlib

matplotlib.use('agg')
import matplotlib.pyplot as plt


def plot_timeheight(config, stid, model, forecast_date, variable, df, plot_dir, img_type):
    """
    Timeseries plotting function

    Currently designed to convert the Profile to a Pandas MultiIndex which is easy to manipulate for plotting.
    Future implementations should probably get rid of the Profile OrderedDict construct altogether.
    """

    # vertical pressure levels (y-coordinates)
    p_levels = np.flip(np.unique(df.index.get_level_values('pressure').values), 0)

    # slice dataframe depending on which variable we are plotting
    # select plotting variables, exclude models that do not have certain variables
    idx = pd.IndexSlice
    if variable == 'temperature':
        temperature = df.loc[idx[:, 'TMPC'], :]
        cmap = 'jet'
        vrange = [-20, 25]
        ytop = 650
        plot_variable = np.ma.masked_array(temperature.values.astype('float'))
        extend = 'both'
    elif variable == 'dewPointDep':
        dewpoint_dep = df.loc[idx[:, 'TMPC'], :].values - df.loc[idx[:, 'DWPC'], :].values
        cmap = 'BrBG_r'
        vrange = [0, 10]
        ytop = 200
        extend = 'max'
        plot_variable = np.ma.masked_array(dewpoint_dep.astype('float'))
    elif variable == 'cloud' and model[0:3] != 'GFS' and model[0:4] != 'HRRR':
        cloud_fr = df.loc[idx[:, 'CFRL'], :]
        cmap = 'Blues_r'
        vrange = [0, 100]
        ytop = 200
        plot_variable = np.ma.masked_array(cloud_fr.values.astype('float'))
        extend = 'neither'
    elif variable == 'windSpeed':
        uwnd = df.loc[idx[:, 'UWND'], :].values.astype('float')
        vwnd = df.loc[idx[:, 'VWND'], :].values.astype('float')
        sknt = np.sqrt(uwnd ** 2 + vwnd ** 2)
        drct = np.ma.masked_array(180 / np.pi * np.arctan2(uwnd, vwnd))
        drct = np.ma.masked_where(np.isnan(drct), drct)
        drct += 180
        drct[np.where((drct < 0))] += 360
        cmap = 'jet'
        ytop = 650
        vrange = [0, int(ceil(np.nanmax(sknt[0:np.where((p_levels == ytop))[0][0], :] / 10.0))) * 10]
        extend = 'neither'
        plot_variable = sknt

        # select values for wind barbs
        barb_heights = [1000., 950., 900., 850., 800., 750., 700.]
        uwnd_barbs = np.zeros((len(barb_heights), len(uwnd[0, :])))
        vwnd_barbs = np.zeros((len(barb_heights), len(uwnd[0, :])))
        for i in range(0, len(barb_heights)):
            uwnd_barbs[i, :] = uwnd[np.where((p_levels == barb_heights[i])), :]
            vwnd_barbs[i, :] = vwnd[np.where((p_levels == barb_heights[i])), :]

        # get boundary-level winds
        bl_df = compute_bl_winds(df)
    elif variable == 'omega':
        omeg = df.loc[idx[:, 'OMEG'], :].values.astype('float')
        cmap = 'seismic'
        ytop = 200
        vrange = [-ceil(np.nanmax(np.abs(omeg) * 10)) / 10., ceil(np.nanmax(np.abs(omeg) * 10)) / 10.]
        extend = 'neither'
        plot_variable = omeg

        # also plot potential temperature contours on omega
        tmpk = df.loc[idx[:, 'TMPC'], :].values.astype('float') + 273.15
        pres = df.loc[idx[:, 'PRES'], :].values.astype('float')
        theta = tmpk * (1000 / pres) ** 0.286
    else:
        if config['debug'] > 50:
            print('%s Bufkit time-height data NOT processed--VARIABLE: %s for MODEL = %s' % (stid, variable, model))
        return

    if config['debug'] > 50:
        print('%s Bufkit time-height data processed--VARIABLE: %s for MODEL = %s' % (stid, variable, model))

    # model times (x-values)
    times = pd.to_datetime(df.loc[idx[:, 'TMPC'], :].columns)

    # set up the plot
    fig = plt.figure()
    fig.set_size_inches(8, 6)
    ax = fig.add_subplot(1, 1, 1)

    # get lower y limit by figuring out which pressure surfaces have data
    pres_surf = np.array(list(zip(*df.loc[idx[:, 'TMPC'], :].apply(pd.Series.first_valid_index).values.tolist()))[0])
    ylims = (np.max(pres_surf), ytop)

    # meshplot of variable
    plot_variable = np.ma.masked_where(np.isnan(plot_variable), plot_variable)
    meshplot = ax.pcolormesh(np.array(times), p_levels, plot_variable, cmap=cmap, vmin=vrange[0], vmax=vrange[1])

    # plot 0 deg C line on temperature plot
    if variable == 'temperature':
        zero_line = plt.contour(times, p_levels, plot_variable, [0.0], colors='k', linewidths=3,
                                linestyles='dashed')
        plt.clabel(zero_line, colors='k', inline_spacing=1, fmt='%1.0f C', rightside_up=True)
    # plot wind barbs and mixed-layer height on wind plot
    if variable == 'windSpeed':
        plt.barbs(matplotlib.dates.date2num(times.to_pydatetime()), barb_heights, uwnd_barbs, vwnd_barbs, length=5.5,
                  lw=0.5)
        bl_line = ax.plot(bl_df.index, bl_df['pressure'], color='red', linewidth=2, linestyle='dashed')
        plt.legend([bl_line[0]], ['Mixed Layer Height'], loc=2)
    if variable == 'omega':
        theta_contours = np.arange(0, 402, 2)
        theta_lines = plt.contour(times, p_levels, theta, theta_contours, colors='k', linewidths=1, linestyles='solid')
        plt.clabel(theta_lines, colors='k', inline_spacing=1, fmt='%d', rightside_up=True, fontsize=8)
        h1, _ = theta_lines.legend_elements()
        plt.legend([h1[0]], ['Potential Temperature (K)'], loc=2, framealpha=0.9)

    # vertical lines at start and end of forecast period
    ax.plot([forecast_date + timedelta(hours=6)] * 2, [p_levels[0], p_levels[-1]], color='k', lw=2.0)
    ax.plot([forecast_date + timedelta(hours=30)] * 2, [p_levels[0], p_levels[-1]], color='k', lw=2.0)
    # label end of model run if it is located on plot
    if times[-1] < (forecast_date + timedelta(hours=40)):
        ax.plot([times[-1]] * 2, [p_levels[0], p_levels[-1]], color='magenta', lw=2.0)
        ax.text(times[-1] + timedelta(hours=1), np.mean(ylims), '(end of model run)', color='magenta', rotation=90,
                ha='center', va='center')

    # Plot configurations and saving
    ax.grid()
    ax.set_title('{} forecast {} time-height at {}'.format(model, variable.upper(), stid))
    ax.set_xlabel('Valid time')
    ax.set_ylabel('Pressure (hPa)')

    # axis range and label formatting
    from matplotlib import dates
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    ax.set_xlim(times[0], forecast_date + timedelta(hours=42))
    ax.set_ylim(ylims)
    ax.xaxis.set_major_locator(dates.HourLocator(byhour=list(range(0, 25, 3))))
    ax.xaxis.set_major_formatter(dates.DateFormatter('%HZ'))
    ax.xaxis.set_minor_locator(dates.DayLocator())
    ax.xaxis.set_minor_formatter(dates.DateFormatter('%h %d'))
    ax.xaxis.set_tick_params(which='minor', pad=15)

    # colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.15)
    plt.colorbar(meshplot, cax, extend=extend)

    # Save plot
    plt.savefig('{}/{}_timeheight_{}_{}.{}'.format(plot_dir, stid, variable.upper(), model, img_type), dpi=150)
    plt.close()
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
    model_date = (forecast_date - timedelta(days=1)).strftime('%Y%m%d')
    file_name = '%s/bufkit/%s%s.%s_%s.buf' % (bufkit_dir, model_date, model_run_hour, bufr_name, stid.lower())
    try:
        infile = open(file_name, 'r')
    except IOError:
        raise IOError('plot.timeheight: missing bufkit file %s' % file_name)

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
            if re.match(r'^\d{3}|^\d{4}', line):
                inblock = False
                block_found = True
            else:
                block_lines.append(''.join(line.split('\r')))  # jweyn: remove any returns

    # Now compute the remaining number of variables
    re_string = ''
    for line in block_lines:
        dum_num = len(line.split())
        for n in range(dum_num):
            re_string = re_string + r'(-?\d{1,5}.\d{2}) '
        re_string = re_string[:-1]  # Get rid of the trailing space
        re_string = re_string + r'\n'

    # Compile this re_string for more efficient re searches
    block_expr = re.compile(re_string)

    # Now get corresponding indices of the variables we need
    full_line = ''
    for r in block_lines:
        full_line = full_line + ''.join(r.split('\n')) + ' '
    # Now split it
    varlist = full_line.strip().split(' ')

    # Variables we want
    vars_desired = ['TMPC', 'DWPC', 'UWND', 'VWND', 'HGHT', 'OMEG', 'CFRL']

    # Pressure levels to interpolate to
    interp_res = 5
    plevs = range(200, 1050, interp_res)

    # We now need to break everything up into a chunk for each
    # forecast date and time
    infile.seek(0)
    blocks = infile.read().split('STID')
    infile.close()
    for block in blocks:
        interp_plevs = []
        header = block
        if header.split()[0] != '=':
            continue
        fcst_time = re.search(r'TIME = (\d{6}/\d{4})', header).groups()[0]
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
            final_vars['UWND'] = list(wspd * np.sin(wdir * np.pi / 180. - np.pi))
        if 'VWND' not in final_vars.keys():
            final_vars['VWND'] = list(wspd * np.cos(wdir * np.pi / 180. - np.pi))
        profile[fcst_dt] = final_vars

    # convert Profile (OrderedDict) into MultiIndex DataFrame
    bufr_vars = list(profile[list(profile.keys())[0]].keys())
    pressure_inds = profile[list(profile.keys())[0]]['PRES'] * len(bufr_vars)
    bufr_vars_inds = np.repeat(bufr_vars, len(profile[list(profile.keys())[0]]['PRES']))
    index = pd.MultiIndex.from_tuples(list(zip(pressure_inds, bufr_vars_inds)), names=['pressure', 'var'])
    df = pd.DataFrame(index=index, columns=list(profile.keys()))

    # populate DataFrame from Profile
    for var in bufr_vars:
        for dt in profile.keys():
            df[dt].loc[:, var] = np.array(profile[dt][var])
    return df


def compute_bl_winds(bufkit_df):
    """
    Computes mixed-layer height and mixed-layer winds from bufkit profiles
    Works by searching for the height where the lapse rate is no longer close to dry adiabatic
    Function written by Luke Madaus, modified by Joe Zagrodnik

    :param bufkit_df: dataframe generated by bufr_timeheight_parser function
    :return: dataframe of mixed-layer height, mean and max mixed-layer wind

    """
    idx = pd.IndexSlice
    tmpc = bufkit_df.loc[idx[:, 'TMPC'], :].values.astype('float')
    hght = bufkit_df.loc[idx[:, 'HGHT'], :].values.astype('float')
    uwnd = bufkit_df.loc[idx[:, 'UWND'], :].values.astype('float')
    vwnd = bufkit_df.loc[idx[:, 'VWND'], :].values.astype('float')
    sknt = np.sqrt(uwnd ** 2 + vwnd ** 2)
    times = pd.to_datetime(bufkit_df.loc[idx[:, 'TMPC'], :].columns)
    p_levels = np.flip(np.unique(bufkit_df.index.get_level_values('pressure').values), 0)

    # Compute the gradients of height and temperature
    dh = np.gradient(hght, axis=0)
    dt = np.gradient(tmpc, axis=0)
    dh_km = dh / 1000.
    dtdz = np.divide(dt, dh_km)

    # dataframe to store boundary layer wind values
    bl_df = pd.DataFrame(index=times, columns=['height', 'pressure', 'mean_wind', 'max_wind'])

    for i in range(0, len(dtdz[0, :])):
        # free atmosphere starts at first level where dT/dZ > -6.0 degC/km
        free_atm = np.where((dtdz[:, i] > -6.0))[0]
        b_loc = np.min(free_atm)
        bl_df['height'][i] = hght[b_loc, i]
        bl_df['pressure'][i] = p_levels[b_loc]
        bl_df['mean_wind'][i] = np.nanmean(sknt[0:b_loc, i])
        bl_df['max_wind'][i] = np.nanmax(sknt[0:b_loc, i])

    return bl_df


def main(config, stid, forecast_date):
    """
    Make timeseries plots for a given station.
    """
    # Use the previous date if we're not at 6Z yet
    if datetime.utcnow().hour < 6:
        forecast_date -= timedelta(days=1)

    # Get the file directory and attempt to create it if it doesn't exist
    try:
        plot_directory = config['Plot']['Options']['plot_directory']
    except KeyError:
        plot_directory = '%s/site_data' % config['THETAE_ROOT']
        print('plot.timeheight warning: setting output directory to default')
    if not (os.path.isdir(plot_directory)):
        os.makedirs(plot_directory)
    if config['debug'] > 9:
        print('plot.timeheight: writing output to %s' % plot_directory)
    try:
        image_type = config['Plot']['Options']['plot_file_format']
    except KeyError:
        image_type = 'svg'
        if config['debug'] > 50:
            print('plot.timeheight warning: using default image file format (svg)')

    # Get list of models
    models = list(config['Models'].keys())

    # List of time-height variables
    variables = ['temperature', 'dewPointDep', 'cloud', 'windSpeed', 'omega']

    # Make plots for models that have a bufkit file
    for model in models:
        if 'bufr_name' in config['Models'][model].keys():
            try:
                df = bufr_timeheight_parser(config, model, stid, forecast_date)
                for variable in variables:
                    if config['debug'] > 50:
                        print('plot.timeheight: plotting %s for %s' % (variable, model))
                    plot_timeheight(config, stid, model, forecast_date, variable, df, plot_directory, image_type)
            except BaseException:
                if config['traceback']:
                    raise
                pass
    return
