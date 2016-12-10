# -*- coding: utf-8 -*-
# flake8: noqa
__author__ = 'Nick Ficano'
__email__ = 'nficano@gmail.com'
__version__ = '0.5.0'

from .aws_lambda import deploy, invoke, init, build, cleanup_old_versions

# Set default logging handler to avoid "No handler found" warnings.
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
