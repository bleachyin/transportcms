#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2011 DuoKan
#

import time
import logging
import Queue, threading
from threading import Thread
from threading import Lock
from common.utilities import Util
from common.jsonconst import COST_TIME_THRESHOLD, MAIL_GROUP_DEVELOPER
from common.jsonconst import HANDLER_THREAD_COUNT, MAX_HANDLER_THREAD_COUNT, TASK_QUEUE_MAX_SIZE,TASK_QUEUE_HWM, TASK_QUEUE_LWM

class _Worker(Thread):
    '''
    worker thread which get task from queu to execute
    '''
    class _ProcessParam(object):
        
        def __init__(self, masterRedis, slaveRedis):
            self._masterRedis = masterRedis
            self._slaveRedis = slaveRedis

        @property
        def masterRedis(self):
            return self._masterRedis
        
        @property
        def slaveRedis(self):
            return self._slaveRedis
        
        def close(self):
            pass

    def __init__(self, threadname, workQueue, parent):
        threading.Thread.__init__(self, name=threadname)
        self.__logger = logging.getLogger(threadname)
        self.__parent = parent
        self.__workQueue = workQueue
        self.stop = False
        
    def run(self):
        masterRedis = Util.get_master_redis_conn()
        slaveRedis = Util.get_slave_redis_conn()
        param = _Worker._ProcessParam(masterRedis = masterRedis,
                                      slaveRedis = slaveRedis)
        while not self.stop:
            try:
                callback= self.__workQueue.get(timeout=2)
                if not callback:
                    continue
                     
                try:
                    startTime = time.time()
                    callback(param)
                    if hasattr(callback, "im_class"):
                        im_class = getattr(callback, "im_class")
                        if hasattr(im_class, "COMMAND_ID"):
                            costTime = time.time() - startTime
                            if costTime > COST_TIME_THRESHOLD: 
                                Util.send_mail_message_queue_by_key(group = MAIL_GROUP_DEVELOPER, 
                                                                    title = "tvservice command warning", 
                                                                    msg = "process command[%d] cost too many times[%f]" % (im_class.COMMAND_ID, costTime),
                                                                    key = "command[%d]" % im_class.COMMAND_ID)          
                except Exception as processEx:
                    self.__logger.error("%s execute callback: %r failed due to %s", self.name, callback, str(processEx), exc_info=1)
            except IOError:
                pass
            except Queue.Empty:
                pass
            except Exception as getEx:
                self.__logger.error("%s get task from queue failed: %s", self.name, getEx, exc_info=1)
            finally:
                if self.__parent.worker_can_exit():
                    self.stop = True
                    
        param.close()
        self.__logger.info("Worker thread[%s] exit",  self.name)        
        self.__parent.notify_worker_exit(self)
        
THREAD_POOL_MAX_COUNT = 128
        
class _WorkerManager(object):
    
    @classmethod
    def instance(cls, minWorkerCount, maxWorkerCount, maxQueueSize):
        if not hasattr(cls, "_instance"):
            cls._instance = cls(minWorkerCount, maxWorkerCount, maxQueueSize)
            cls.__logger = logging.getLogger("thread_pool")
        return cls._instance
    
    def __init__(self, workerCount=HANDLER_THREAD_COUNT, maxCount=MAX_HANDLER_THREAD_COUNT, maxQueueSize=TASK_QUEUE_MAX_SIZE):
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__workQueue = Queue.Queue(maxsize=maxQueueSize)
        self.__minWorkerCount = workerCount
        self.__maxWorkerCount = maxCount
        self.__lowWaterMark = TASK_QUEUE_LWM
        self.__highWaterMark = TASK_QUEUE_HWM
        self.__mutex = Lock()
        self.__workers = set()
        self.__initialized = False
        
    def initialize(self):                      
        for i in xrange(self.__minWorkerCount):
            worker = _Worker("_Worker-" + str(i + 1), self.__workQueue, self)
            worker.start()
            self.__workers.add(worker)
        self.__initialized = True
            
    @property
    def maxWorkers(self):
        return self.__maxWorkerCount
    
    @maxWorkers.setter
    def maxWorkers(self, maxCount):
        if self.__minWorkerCount <= maxCount <= THREAD_POOL_MAX_COUNT:
            self.__maxWorkerCount = maxCount
        else:
            raise ValueError("WorkerManager setting max worker count[%s] is overflow" % maxCount)
    
    @property
    def minWorkers(self):
        return self.__minWorkerCount
    
    @minWorkers.setter
    def minWorkers(self, minCount):     
        if 0 <= minCount <= self.__maxWorkerCount:
            self.__minWorkerCount = minCount
        else:
            raise OverflowError("WorkerManager setting min worker count[%s] is invalid" % minCount)
        
    @property
    def highWaterMark(self):
        return self.__highWaterMark
    
    @highWaterMark.setter
    def highWaterMark(self, hwm):
        if hwm < self.__workQueue.maxsize:
            self.__highWaterMark = hwm
        else:
            raise OverflowError("WorkerManager setting high water mark[%s] is overflow" % hwm)
        
    @property
    def lowWaterMark(self):
        return self.__lowWaterMark
    
    @lowWaterMark.setter
    def lowWaterMark(self, lwm):
        if lwm < (self.__workQueue.maxsize >> 2):
            self.__lowWaterMark = lwm
        else:
            raise ValueError("WorkerManager setting low water mark[%s] is invalid" % lwm)   

    @property
    def currentLoad(self):
        return self.__workQueue.qsize()

    def stop(self):
        ''' Wait for each of them to terminate'''
        with self.__mutex:
            self.__initialized = False
            while self.__workers:
                worker = self.__workers.pop()
                worker.stop = True
                self.__workQueue.put(None)            
            
    def add_task(self, callback):
        if not self.__initialized:
            raise AttributeError("WorkerManager does not initialized before calling add_task method")
        
        self.__workQueue.put(callback, block=False)
        if self.__workQueue.qsize() >= self.__highWaterMark:
            with self.__mutex:
                if len(self.__workers) < self.__maxWorkerCount:
                    worker = _Worker("_Worker-" + str(len(self.__workers)), self.__workQueue, self)
                    worker.start()
                    self.__workers.add(worker)
                    self.__logger.info("Dynamic add new worker thread[%s]", worker.name)
        
    def notify_worker_exit(self, worker):
        with self.__mutex:
            self.__workers.discard(worker)
        
    def worker_can_exit(self):
        with self.__mutex:
            workerCondition = len(self.__workers) > self.__minWorkerCount
        return workerCondition and self.__workQueue.qsize() <= self.__lowWaterMark
        
ThreadPool = _WorkerManager.instance(HANDLER_THREAD_COUNT, MAX_HANDLER_THREAD_COUNT, TASK_QUEUE_MAX_SIZE)            