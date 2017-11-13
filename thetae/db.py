#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Functions for interfacing with the SQL database.
'''

import sqlite3
import os

def db_conn(config, data_binding):
    '''
    Initializes a connection to the database. We only need to check for errors
    in the config file here, because the main program will try to establish
    a connection before making any further progress.
    '''
    db_dir = '%s/archive' % config['THETAE_ROOT']
    if not(os.path.isdir(db_dir)):
        try:
            os.system('mkdir -p %s' % db_dir)
        except:
            print('Error: could not access database directory')
            return
    # Check that the database is defined
    if not(data_binding in list(config['Databases'].keys())):
        print('Error: database not defined in config file under "Databases"')
        return
    try:
        db_name = '%s/%s' % (db_dir,
                             config['Databases'][data_binding]['database_name'])
    except:
        print('Error: database name error in config file')
        return
    # Establish a connection
    try:
        conn = sqlite3.connect(db_name)
    except:
        print('Error connecting to database %s' % db_name)

    return conn

def db_init(config):
    '''
    Initializes a new station ID in the database.
    '''
    # Find the schema
    from util import _get_object
    for data_binding in list(config['DataBinding'].keys()):
        schema_name = config['DataBinding'][data_binding]['schema']
        schema = _get_object(schema_name).schema
        conn = db_conn(config, data_binding)
        
    return



