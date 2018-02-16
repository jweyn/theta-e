#
#
#
#

from datetime import datetime, timedelta
from highcharts import Highchart
#import sqlite3
import pandas as pd
import pdb
from thetae.db import db_readTimeSeries

"""
Generates timeseries plot for various models
"""

def plot_timeseries(config, stid, models, forecast_date, variable):
    """
    Timeseries plotting function
    Eventually will only output the JSON but for now set up to make a test plot
    """

    # Current time
    time_now = datetime.utcnow()

    # Create highchart object
    chart = Highchart()

    # Set plot bounds
    forecast_start = forecast_date + timedelta(hours=6)
    forecast_end = forecast_date + timedelta(hours=30)
    plot_start = forecast_date - timedelta(hours=18)
    plot_end = forecast_end + timedelta(hours=18)

    # Define various strings for the plot
    var_string = variable[0]+variable[1:].lower()
    subtitle = 'Last updated: {}'.format(time_now.strftime('%Y %b-%d %H:%M UTC'))

    for model in ['GFS MOS', 'NAM MOS' , 'UKMET']:
        timeseries = db_readTimeSeries(config, stid, 'forecast', 'HOURLY_FORECAST', model=model, start_date=plot_start, end_date=plot_end)
        temp_data = timeseries.data[['DATETIME','TEMPERATURE']]#.to_json(orient='split')
        time_data = pd.to_datetime(timeseries.data['DATETIME'])
        stupid_data = []
        for i in len(time_data):
            stupid_data.append([time_data[i],temp_data['TEMPERATURE'][i]])
 
        chart.add_data_set(stupid_data, series_type='spline', name=model)


    options = {
        'title': {
            'text': '{} Forecast {}'.format(stid,var_string)
        },
        'subtitle': {
            'text': subtitle
        },
        'xAxis': {
            'reversed': False,
            'type' : 'datetime',
            'title': {
                'enabled': True,
                'text': 'Time'
            },
            'maxPadding': 0.05,
            'showLastLabel': True
        },
        'yAxis': {
            'title': {
                'text': 'Temperature (F)'
            },
            'labels': {
                'formatter': "function () {\
                    return this.value + ' ';\
                }"
            },
            'lineWidth': 2
        },
        'legend': {
            'enabled': True
        },
        'tooltip': {
            'headerFormat': '<b>{series.name}</b><br/>',
            'xDateFormat: "%Y-%m-%d"'
            'pointFormat': '{point.x} UTC: {point.y} F'
        }
    }

    chart.set_dict_options(options)
    chart.save_file('{}{}_{}_timeseries'.format(config['THETAE_WEB'],stid,variable.lower()))


'''

H = Highchart()

data_Tokyo = [7.0, 6.9, 9.5, 14.5, 18.2, 21.5, 25.2, 26.5, 23.3, 18.3, 13.9, 9.6]
data_NY = [-0.2, 0.8, 5.7, 11.3, 17.0, 22.0, 24.8, 24.1, 20.1, 14.1, 8.6, 2.5]
data_Berlin = [-0.9, 0.6, 3.5, 8.4, 13.5, 17.0, 18.6, 17.9, 14.3, 9.0, 3.9, 1.0]
data_London = [3.9, 4.2, 5.7, 8.5, 11.9, 15.2, 17.0, 16.6, 14.2, 10.3, 6.6, 4.8]

H.add_data_set(data_Tokyo, 'line', 'Tokyo')
H.add_data_set(data_NY, 'line', 'New York')
H.add_data_set(data_Berlin, 'line', 'Berlin')
H.add_data_set(data_London, 'line', 'London')

H.set_options('title', {'text': 'KSEA Temperature Forecast'})

H.set_options('chart', {'zoomType': 'x'})
H.set_options('xAxis', {'categories': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
	'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']})

H.set_options('yAxis',{ 'title': { 'text': 'Temperature (F)'},
            'plotLines': {'value': 0, 'width': 1, 'color': '#808080'}})
H.set_options('tooltip', {'valueSuffix': 'F'})

H.set_options('legend', {'layout': 'vertical','align': 'right',
	'verticalAlign': 'middle','borderWidth': 0})
H.set_options('colors',{})
H.set_options('plotOptions',{'line': {
                'dataLabels': {
                    'enabled': True
                }}})

#need to print the table
chart.save_file('/home/disk/meso-home/jzagrod/public_html/thetae/temperature_timseries')
pdb.set_trace()
'''

def main(config, stid, forecast_date):
    """
    Make a timeseries plot
    """

    # Get list of models
    models = config['Models'].keys()
    
    # Define variables. Possibly move this to config later
    variables = ['TEMPERATURE']

    # Get forecast
    for variable in variables:
        plot_timeseries(config, stid, models, forecast_date, variable)

    return
