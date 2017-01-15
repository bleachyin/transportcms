#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 DuoKan
#

from queue.mongoqueue import MongoQueue

class QueueFactory(object):

    @classmethod
    def instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        pass
    
    def get_mongo_queue(self, host, database, queue, queue_size=4096, message_size=1024, thread_safe=True):
        return MongoQueue(host=host, database=database, queue=queue, queue_size=queue_size, average_message_size=message_size, thread_safe=thread_safe)
    