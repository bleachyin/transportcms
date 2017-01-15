#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2011 DuoKan
#

import logging

from common.fakeredis import FakeRedis

class _RedisPool(object):
    
    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
            cls._logger = logging.getLogger("redis_pool")
        return cls._instance
    
    def get_master_redis(self):
        return self._redis
        
    def get_slave_redis(self):
        return self._redis
    
    def get_redis(self):
        return self._redis
    
    def initialize(self):
        self._redis =  FakeRedis()
        self._logger.info("Redis connection pool initialize success.")
    
RedisPool = _RedisPool.instance()
                