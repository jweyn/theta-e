#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Initialize thetae.
'''

__version__ = '0.0.1'

# =============================================================================
# Service groups.
# =============================================================================

all_service_groups = [
    'retrieve_services', 'database_services', 'output_services']

# =============================================================================
# Get configuration.
# =============================================================================

def getConfiguration(config_path):
    '''
    Retrieve the config dictionary from config_path.
    '''
    import configobj
    try:
        config_dict = configobj.ConfigObj(config_path, file_error=True)
    except IOError:
        print("Error: unable to open configuration file %s" % config_path)
        raise
    except configobj.ConfigObjError, e:
        print("Error while parsing configuration file %s" % config_path)
        print("    Reason: '%s'" % e)
        raise
    
    if int(config_dict['debug']) > 1:
        print("Using configuration file %s" % config_path)

    return config_dict
