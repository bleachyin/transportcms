import logging
__author__ = 'bleach_yin'


class BaseHandler(object):

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        
        