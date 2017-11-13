#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Default schema for the theta-e SQLite database. The actual tables have the
4-letter station ID appended to the beginning of the schema keys. The tables
represent:
    XXXX_OBS: time series of hourly observations
    XXXX_HOURLY_FORECAST: time series of hourly forecasts from various sources
    XXXX_VERIF: individual days' verified high, low, wind, and rain
    XXXX_DAILY_FORECAST: model forecasts of next day's high, low, wind, and rain
    XXXX_CLIMO: climatological yearly norms, populated once
'''

schema = {
'_OBS': [
    ('DateTime',        'STRING NOT NULL UNIQUE PRIMARY KEY'),
    ('temperature',     'REAL'),
    ('dewpoint',        'REAL'),
    ('cloud',           'REAL'),
    ('windSpeed',       'REAL'),
    ('windDirection',   'REAL'),
    ('rainHour',        'REAL'),
    ('condition',       'STRING')
         ],
'_HOURLY_FORECAST': [
    ('DateTime',        'STRING NOT NULL UNIQUE PRIMARY KEY'),
    ('Model',           'STRING'),
    ('temperature',     'REAL'),
    ('dewpoint',        'REAL'),
    ('cloud',           'REAL'),
    ('windSpeed',       'REAL'),
    ('windDirection',   'REAL'),
    ('rainHour',        'REAL'),
    ('condition',       'STRING')
              ],
'_VERIF': [
    ('DateTime',        'STRING NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ],
'_DAILY_FORECAST': [
    ('DateTime',        'STRING NOT NULL UNIQUE PRIMARY KEY'),
    ('Model',           'STRING'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
                    ],
'_CLIMO': [
    ('DateTime',        'STRING NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ]
}
