#
# Copyright (c) 2019 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Initialize thetae.
"""

__version__ = '0.0.3'


# ==============================================================================
# Service groups.
# ==============================================================================

all_service_groups = [
    'retrieve_services', 'calc_services', 'output_services'
]


# ==============================================================================
# Exception classes
# ==============================================================================

class MissingDataError(Exception):
    pass


# ==============================================================================
# Make sure we import everything we need.
# ==============================================================================

# Current-level module imports. 'engine' depends on 'all_service_groups' above.
from . import db
from . import engine
from . import getForecasts
from . import getVerification
from . import calcVerification
from . import util
from .util import Forecast, Daily, TimeSeries
