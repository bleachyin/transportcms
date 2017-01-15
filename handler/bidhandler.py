# -*- coding: utf-8 -*- 
from common.database import DBConnPool
from common.bidconst import *
from conf.settings import DB_NAME
from handler.basehandler import BaseHandler
import logging
import pymongo
import time
import datetime
import math
from handler.planhandler import PlanHandler


class BidHandler(BaseHandler):
    
    def __init__(self):
#         self._logger = logging.getLogger(self.__class__.__name__)
        super(BidHandler, self).__init__()
        
    def init_bid_data(self):
        conn = DBConnPool.get_collection(DB_NAME,"bid_user")
        conn2 = DBConnPool.get_collection(DB_NAME,"bid_plan")
        conn.remove()
        conn2.remove()
        conn3 = DBConnPool.get_collection(DB_NAME,"plan")
        last = None
        for index,bidname in enumerate(BID_BUILD):
            id = index+1
            conn.update({"_id":id},{"$set":{"name":bidname,"type":BID_BUILD_TYPE}},upsert=True)
#             copyplans = conn3.find({"_id":{"$in":BID_BUILD_SCOPE}})
            copyplans = conn3.find({"_id":{"$lte":BID_BUILD_SCOPE[1],"$gte":BID_BUILD_SCOPE[0]}})
            for copyplan in copyplans:
                planid = copyplan['_id']
                copyplan['changed'] =  False
                copyplan.pop("_id")
                conn2.update({"id":planid,"userid":id},{"$set":copyplan},upsert=True)
            last = id
        for index,bidname in enumerate(BID_DES):
            lastid = last+index+1
            conn.update({"_id":lastid},{"$set":{"name":bidname,"type":BID_DES_TYPE}},upsert=True)
#             copyplans = conn3.find({"_id":{"$in":BID_DES_SCOPE}})
            copyplans = conn3.find({"_id":{"$lte":BID_DES_SCOPE[1],"$gte":BID_DES_SCOPE[0]}})
            for copyplan in copyplans:
                planid = copyplan['_id']
                copyplan['changed'] =  False
                copyplan.pop("_id")
                conn2.update({"id":planid,"useid":lastid},{"$set":copyplan},upsert=True)
    
    def plan_by_rank_and_bid(self,bidid,rank):
        bidview = {}
        conn = DBConnPool.get_collection(DB_NAME,"bid_plan")
        results = conn.find({"userid":bidid}).sort("id",pymongo.ASCENDING).skip(rank-1).limit(1)
        total = conn.find({"userid":bidid}).count()
        if results:
            bidview = self.bid_cal_view(results[0].get('cal',{}))
        return results,total,bidview
    
    def bid_cal_view(self,cal):
        cal2 = {}
        start_adv = cal['start_adv']
        start_delay = cal['start_delay']
        end_adv = cal['end_adv']
        end_delay = cal['end_delay']
        plan_day = cal['plan_day']
        real_day = cal['real_day']
        performace = cal['performace']
        day_mag = float(math.pow(10, max(plan_day,real_day)/10+1))
        start_mag = float(math.pow(10,max(start_adv,start_delay)/10+1))
        end_mag = float(math.pow(10,max(end_adv,end_delay)/10+1))
        # if cal:
        #     cal2['start_adv'] = float(start_adv)
        #     cal2['start_delay'] = float(cal['start_delay'])
        #     cal2['end_adv'] = float(cal['end_adv'])/base
        #     cal2['end_delay'] = float(cal['end_delay'])/base
        #     cal2['plan_day'] = float(cal['plan_day'])/base
        #     cal2['real_day'] =  float(cal['real_day'])/base
        #     cal['performace'] = float(cal['performace']/base)
        return cal2
    
    # def _get_
        
    
    def plan_save_by_rank_and_bid(self,start_date,end_date,bidid,id,rank):
        conn = DBConnPool.get_collection(DB_NAME,"bid_plan")
        planinfo = conn.find_one({"id":id,"userid":bidid})
        d1 = None
        d2 = None
        if start_date:
            start_secs = int(time.mktime(datetime.datetime.strptime(start_date,'%Y-%m-%d').timetuple()))
            d1 = datetime.datetime.fromtimestamp(start_secs)
            planinfo['start_secs'] =  start_secs
            planinfo['start_date'] = d1.strftime('%Y-%m-%d')
        else:
            d1 = datetime.datetime.fromtimestamp(planinfo['start_secs'])
        if end_date:
            end_secs = int(time.mktime(datetime.datetime.strptime(end_date,'%Y-%m-%d').timetuple()))
            d2 = datetime.datetime.fromtimestamp(end_secs)
            planinfo['end_secs'] =  end_secs
            planinfo['end_date'] = d2.strftime('%Y-%m-%d')
        else:
            d2 = datetime.datetime.fromtimestamp(planinfo['end_secs'])
        if d1 and d2:
            planinfo['day'] =  (d2-d1).days
        planinfo['changed'] = True
        planinfo.pop("_id")
        orplaninfo = PlanHandler().plan_by_id(planinfo['id'])
        planinfo["cal"] = self._calculate_performance(planinfo, orplaninfo)
        conn.update({"id":id,"userid":bidid},{"$set":planinfo},upsert=True)
        
    def _calculate_performance(self,planinfo,orplaninfo):
        cal = {}
        d1 = datetime.datetime.fromtimestamp(planinfo['start_secs'])
        d2 = datetime.datetime.fromtimestamp(orplaninfo['end_secs'])
        d3 = datetime.datetime.fromtimestamp(planinfo['end_secs'])
        d4 = datetime.datetime.fromtimestamp(orplaninfo['end_secs'])
        if orplaninfo['start_secs'] > planinfo['start_secs']:
            cal['start_adv'] = (d2-  d1).days
            cal['start_delay'] = 0
        else:
            cal['start_adv'] = 0
            cal['start_delay'] = (d1 -  d2).days
        if orplaninfo['end_secs'] > planinfo['end_secs']:
            cal['end_adv'] = (d4-d3).days
            cal['end_delay'] = 0
        else:
            cal['end_adv'] = 0
            cal['end_delay'] = (d3-d4).days
        cal['plan_day'] = orplaninfo['day']
        cal['real_day']  =  planinfo['day']
        cal['performace'] =  100 - (float(50*(abs(cal['plan_day']-cal['real_day']))- 25*cal['start_adv'] - 25*cal['start_delay']-25*cal['end_adv']-25*cal['end_delay'])/365.0)
        return cal