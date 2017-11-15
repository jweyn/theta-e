#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Default schema for the theta-e SQLite database. Use this structure to create any
user database schemas.
The first column in any table MUST be the datetime column. This is used for
indexing and retrieving data. An optional column name of 'PRIMARY KEY' may be
used to assign a composite index to a table. That is the only column name that
will be ignored when attempting to write data to the database.

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
    ('DateTime',        'TEXT NOT NULL'),
    ('Model',           'TEXT'),
    ('temperature',     'REAL'),
    ('dewpoint',        'REAL'),
    ('cloud',           'REAL'),
    ('wind',            'REAL'),
    ('windDirection',   'REAL'),
    ('rain',            'REAL'),
    ('condition',       'TEXT'),
    ('PRIMARY KEY',     '(DateTime, Model)') # make composite key
              ],
'_VERIF': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ],
'_DAILY_FORECAST': [
    ('DateTime',        'TEXT NOT NULL'),
    ('Model',           'TEXT'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL'),
    ('PRIMARY KEY',     '(DateTime, Model)')
                    ],
'_CLIMO': [
    ('DateTime',        'TEXT NOT NULL UNIQUE PRIMARY KEY'),
    ('high',            'REAL'),
    ('low',             'REAL'),
    ('wind',            'REAL'),
    ('rain',            'REAL')
           ]
}
