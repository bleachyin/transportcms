#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2013 DuoKan
#
import logging
import time
import uuid
import pymongo
from threading import Lock

import queue.queuebase
from queue.message import Message

class MongoQueue(queue.queuebase.QueueBase):
    
    ALREADY_EXISTS_EXCEPTION_STRING = 'collection already exists'

    def __init__(self,
        host='localhost',
        port=27017,
        database='queuedb',
        queue='messages',
        average_message_size=1024,
        queue_size=4096,
        thread_safe=True):
        self.host = host
        self.port = port
        self.database = database
        self.queue = queue
        self.average_message_size = average_message_size
        self.queue_size = queue_size
        self.thread_safe = thread_safe
        if self.thread_safe:
            self.__mutex = Lock()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._create_mongo_connection()
        
    def _create_mongo_connection(self):
        self.connection = pymongo.Connection(
            self.host,
            self.port
        )
        self.queue_database = self.connection[self.database]
        self.queue_collection = self.queue_database[self.queue]
        self._create_capped_collection()
        
    def _create_capped_collection(self):
        try:
            pymongo.collection.Collection(
                self.connection[self.database],
                self.queue,
                size = (self.average_message_size * self.queue_size),
                capped = True,
                max = self.queue_size,
                create = True,
                safe = True
            )
             
            self.queue_collection.create_index('_id')
            self.queue_collection.create_index('_meta.routing_key')
            self.queue_collection.create_index('_meta.unique_key', unique=True, dropDups=True)
            self.queue_collection.create_index('_meta.expired')
            
        except pymongo.errors.OperationFailure, operation_failure:
            if not self.ALREADY_EXISTS_EXCEPTION_STRING in str(operation_failure):
                self._logger.warn("Create queue: %s failed, due to: %s", self.queue, str(operation_failure), exc_info=1)
            
    def _lock(self):
        if self.thread_safe:
            self.__mutex.acquire()
            
    def _unlock(self):
        if self.thread_safe:
            self.__mutex.release()
        
    def write(self, message, routing_key=None, expire=-1.0, unique_key=None):
        self._lock()
        try:
            if type(message) == dict:
                message_dict = message
            else:
                message_dict = message.to_dictionary()
                
            message_dict['_meta'] = {}
            message_dict['_meta']['expired'] = False
            message_dict['_meta']['timestamp'] = time.time()
            message_dict['_meta']['expire'] = expire
            
            if routing_key:
                message_dict['_meta']['routing_key'] = routing_key
            
            if unique_key is None:
                message_dict['_meta']['unique_key'] = uuid.uuid4().hex
                self.queue_collection.insert(message_dict, w=1)
                return True
            else:
                message_dict['_meta']['unique_key'] = unique_key
                spec_dict = {"_meta.unique_key":unique_key}
                existence = self.queue_collection.find_one(spec_dict, {"_id":1, "_meta.expired":1, "_meta.unique_key":1})
                if existence is None:
                    self.queue_collection.insert(message_dict, w=1)
                elif existence['_meta']['expired']:
                    spec_dict['_id'] = existence['_id']
                    self.queue_collection.update(spec_dict, message_dict, upsert=True, w=1)
                return True
        finally:
            self._unlock()
    
    def read(self, routing_key=None, messages_read=10, block=False, polling_interval=1.0, polling_timeout=None):
        self._lock()
        try:  
            query = {
                '_meta.expired': False,
            }
            if routing_key:
                query['_meta.routing_key'] = routing_key
            else:
                query['_meta.routing_key'] = {'$exists': False}
                            
            if block:
                self._block_until_message_available(query, polling_interval, polling_timeout)            
                
            update = {
                '$set': {
                    '_meta.expired': True
                }
            }
            raw_messages=[]
            for i in xrange(messages_read):
                raw_message = self.queue_collection.find_and_modify(query=query, update=update)
                if raw_message:
                    raw_messages.append(raw_message)
                else:
                    break
                    
            messages = []
            for raw_message in raw_messages:
                message = Message(dictionary=raw_message, queue_collection=self.queue_collection)
                
                if not message.is_expired():
                    messages.append(message)
                
            return messages
        finally:
            self._unlock()
    
    def _block_until_message_available(self, query, polling_interval, polling_timeout):
        current_time = time.time()
        while self.queue_collection.find(query).count() == 0:
            if polling_timeout and (time.time() - current_time) > polling_timeout:
                break
            time.sleep(polling_interval)        