# -*- coding: utf-8 -*- 
# 文件名: database.py
# 摘  要: MySQLdb封装

import pymongo
import ConfigParser
import hashlib
#from karait import Message, Queue
from queue.queuefactory import QueueFactory


class MongoAccount(object):
    """
    mysql account
    """
    def __init__(self, user, passwd, sock, dbsize):
        self.user = user
        self.passwd = passwd
        self.sock = sock
        self.dbsize = dbsize

def load_dbconfig(dbname, conf_file):
    """
    load dbconfig according to block name
    """
    cf = ConfigParser.ConfigParser()
    cf.read(conf_file)
    account = MongoAccount(cf.get(dbname, "db_user"), cf.get(dbname, "db_pass"),
                            cf.get(dbname, "db_sock"), cf.get(dbname, "db_size"))
    return account
    
class DBConnection(object):
    """
    mongodb的简单封装
    """
        
    def connect(self, dba):
        """
        connect to mongodb
        """
        self.__dba = dba
        self.__dbsize = dba.dbsize 
        if self.__dba.passwd and self.__dba.user:
            self.mongoUrl = 'mongodb://%s:%s@%s' % (self.__dba.user, self.__dba.passwd, self.__dba.sock)
        else:
            self.mongoUrl ='mongodb://%s' % (self.__dba.sock)
        readPreference = pymongo.read_preferences.ReadPreference.SECONDARY_PREFERRED
        writePreference = pymongo.read_preferences.ReadPreference.PRIMARY_PREFERRED
        self.readMongoConnection = pymongo.connection.Connection(self.mongoUrl, max_pool_size=self.__dbsize, read_preference = readPreference)
        self.writeMongoConnection = pymongo.connection.Connection(self.mongoUrl, max_pool_size=self.__dbsize, read_preference = writePreference)
        self.queueInstance = QueueFactory.instance()
#         self.message_queue = self.queueInstance.get_mongo_queue(host=self.mongoUrl, database=TV_DB_NAME, queue_size=10000, queue='servicequeue')
        
        return True
    
    def disconnect(self):
        self.readMongoConnection.disconnect()
        self.writeMongoConnection.disconnect()
    
    def get_collection(self, dbname, collectionName):
        return self.readMongoConnection[dbname][collectionName]

    def get_write_collection(self, dbname, collectionName):
        return self.writeMongoConnection[dbname][collectionName]
    
#     def send_genernate_package_message(self, msg, uniqueKey):
#         self.message_queue.write(msg, routing_key='router_upgrade', unique_key=uniqueKey)
#         
#     def send_upgradeinfo_message(self, msg, uniqueKey):
#         self.message_queue.write(msg, routing_key='clojureupgrade', unique_key=uniqueKey)
        
#     def send_mail_message_queue(self, group, msg):
#         msgMd5 = hashlib.md5(str(group) + "_"+str(msg)).hexdigest().upper()
#         self.message_queue.write({"group":group,  "host":LOCAL_HOST_NAME, "title":"tvservice发生异常", "msg":msg}, routing_key='mail_nor', unique_key=msgMd5)
#         
#     def send_mail_message_queue_by_key(self, group, title, msg, key):
#         self.message_queue.write({"group":group,  "host":LOCAL_HOST_NAME, "title":title, "msg":msg}, routing_key='mail_nor', unique_key=key)        
        
DBConnPool = DBConnection()
