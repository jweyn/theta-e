#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Default schema for the theta-e SQLite database. Use this structure to create any
user database schemas.
The actual tables have the 4-letter station ID appended to the beginning of the
schema keys. The tables represent:
    XXXX_OBS: time series of hourly observations
    XXXX_HOURLY_FORECAST: time series of hourly forecasts from various sources
    XXXX_VERIF: individual days' verified high, low, wind, and rain
    XXXX_DAILY_FORECAST: model forecasts of next day's high, low, wind, and rain
    XXXX_CLIMO: climatological yearly norms, populated once
'''

schema = {
'_OBS': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('temperature',     'REAL'),
    ('dewpoint',        'REAL'),
    ('cloud',           'REAL'),
    ('windSpeed',       'REAL'),
    ('windDirection',   'REAL'),
    ('rainHour',        'REAL'),
    ('condition',       'TEXT')
         ],
'_HOURLY_FORECAST': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('Model',           'TEXT'),
    ('temperature',     'REAL'),
    ('dewpoint',        'REAL'),
    ('cloud',           'REAL'),
    ('windSpeed',       'REAL'),
    ('windDirection',   'REAL'),
    ('rainHour',        'REAL'),
    ('condition',       'TEXT')
              ],
'_VERIF': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ],
'_DAILY_FORECAST': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('Model',           'TEXT'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
                    ],
'_CLIMO': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ]
}
