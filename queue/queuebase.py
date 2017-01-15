#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 DuoKan
#

class QueueBase(object):

    def __init__(self):
        pass
    
    def write(self, message, routing_key=None, expire=-1.0, unique_key=None):
        raise NotImplementedError()
    
    def read(self, routing_key=None, messages_read=10, block=False, polling_interval=1.0, polling_timeout=None):
        raise NotImplementedError()
    
    def delete_messages(self, messages):
        pass