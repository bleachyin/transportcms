#
# Copyright 2011 DuoKan
#

import logging
import Queue
from common.mysqldatabase import DBConnection

class _ConnectionPool(object):
        
    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        
    def initialize(self, account, maximum):
        self._logger.info("Initialize DB connection poll, the maximum is: %s", str(maximum))
        self._connections = Queue.Queue()
        for i in range(maximum):
            try:
                conn = DBConnection(account)
            except Exception as ex:
                self._logger.error("Create %d DB connection failed: %r", i, ex)
                raise
            else:
                self._connections.put(conn)
        return True
    
    def close(self): 
        while self._connections:
            conn = self._connections.get(True)
            conn.close()

    def get_connection(self, timeout=None):
        return self._connections.get(True, timeout)
        
    def free_connection(self, conn):
        if isinstance(conn, DBConnection):
            return self._connections.put(conn)
            
        raise AttributeError("Unrecognized connection %r" % conn)

MasterConnPool = _ConnectionPool()
MasterLogConnPool = _ConnectionPool()