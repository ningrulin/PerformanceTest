#!/usr/bin/env python
import logging
class Logger(object):
    logger=None
    def __init__(self):
        pass
    @classmethod
    def getLogger(cls):
        if Logger.logger is None:
            Logger.logger=logging.getLogger("MXTest")
            # Logger.logger = logging.getLogger('mylogger')
            # Logger.logger.setLevel(logging.DEBUG)
            # fh = logging.FileHandler('test.log')
            # fh.setLevel(logging.DEBUG)
            # ch = logging.StreamHandler()
            # ch.setLevel(logging.DEBUG)
            # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            # fh.setFormatter(formatter)
            # ch.setFormatter(formatter)
            # Logger.logger.addHandler(fh)
            # Logger.logger.addHandler(ch)
        return Logger.logger
    @classmethod
    def debug(cls,msg):
        # pass
        Logger.getLogger().debug(msg)
    @classmethod
    def error(cls,msg):
        Logger.getLogger().error(msg)