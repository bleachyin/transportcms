# -*- coding: utf-8 -*- 
from common.database import DBConnPool
from common.jsonconst import STAGING_PROCESS
from conf.settings import DB_NAME
from handler.basehandler import BaseHandler
import pymongo
import ujson
import sys
import logging
import datetime
import time
import xlsxwriter
import os
reload(sys)
sys.setdefaultencoding('utf-8')

#row col
xls_name = 7
xls_child_name = 6
xls_child_day = 4
xls_child_finish = 4

class PlanHandler(BaseHandler):


    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        super(PlanHandler, self).__init__()
    
    def _get_stage_from_db(self, rank):
        conn = DBConnPool.get_collection(DB_NAME, "plan")
        total = conn.find().count()
        results = conn.find().sort("_id",pymongo.ASCENDING).skip(rank-1).limit(1)
        return results,total
    
    def plan_by_id(self,planid):
        conn = DBConnPool.get_collection(DB_NAME, "plan")
        planinfo = conn.find_one({"_id":planid})
        return planinfo 
    
    def plan_by_rank(self,rank):
        results,total = self._get_stage_from_db(rank)
        return results, total
            
    def _read_settings(self):
        conn = DBConnPool.get_collection(DB_NAME, "plan")
        conn.remove()
        for index, stage in enumerate(STAGING_PROCESS):
            for peroid_index , peroid in enumerate(stage):
                parentname, children = peroid
                stageid = index+1
#             conn.update({"_id":parentid},{"$set":{"name":parentname,"stage":stageid,"leaf":False,"leafsize":leafsize}},upsert=True)
                for rank,child in enumerate(children):
                    childid = (index+1)*1000+peroid_index*100+rank
                    childname, day = child
                    print childid,parentname,childname
                    conn.update({"_id":childid},{"$set":{"parentname":parentname,"name":childname,"stage":stageid,"day":day}},upsert=True)
    
    def init_trans_data(self):
        conn = DBConnPool.get_collection(DB_NAME, "plan")
        conn.remove()   
        self._read_settings()

    def get_base_information(self):
        conn = DBConnPool.get_collection(DB_NAME, "base")
        base_info = conn.find_one({"_id":1})
        if not base_info:
            return {}
        else:
            return self._build_base_info(base_info)

    def _build_base_info(self,base_info):
        if "finish_date" in base_info:
            base_info['finish_date'] =  datetime.datetime.fromtimestamp(base_info['finish_date']).strftime("%Y-%m-%d")
        return base_info

    def init_trans_data_with_date(self,id, start_date,end_date,rank):
        conn =  DBConnPool.get_collection(DB_NAME,"plan")
        results = list(conn.find().sort("_id",pymongo.ASCENDING))
        curr = conn.find().sort("_id",pymongo.ASCENDING).skip(rank-1).limit(1)[0]
        prevlist = results[0:rank]
        afterlist = results[rank:]
        start_secs =None
        end_secs =None
        if start_date:
            start_secs = int(time.mktime(datetime.datetime.strptime(start_date,'%Y-%m-%d').timetuple()))
        if end_date:
            end_secs = int(time.mktime(datetime.datetime.strptime(end_date,'%Y-%m-%d').timetuple()))
        if not start_secs and end_secs:
            curr['start_secs'] = end_secs - curr['day']*3600*24
            curr['end_secs'] = end_secs
        if start_secs and not end_secs:
            curr['start_secs'] =  start_secs
            curr['end_secs'] = curr['day']*3600*24 + start_secs
        if start_secs and end_secs:
            curr['start_secs'] = start_secs
            curr['end_secs'] = end_secs
        else:
            return
        conn.update({"_id":id},{"$set":{"start_secs":curr['start_secs'],"end_secs":curr['end_secs']}})
        prev_last = curr
        after_last = curr
        for prev in reversed(prevlist):
            prev['end_secs'] = prev_last['start_secs']
            prev['start_secs'] =  prev['end_secs'] - prev['day']*3600*24
            prev_last = prev
            conn.update({"_id":prev['_id']},{"$set":{"start_secs":prev['start_secs'],"end_secs":prev['end_secs']}},w=1)
        for after in afterlist:
            after['start_secs'] = after_last['end_secs']
            after['end_secs'] = after['day']*3600*24 + after_last['start_secs']
            after_last = after
            conn.update({"_id":after['_id']},{"$set":{"start_secs":after['start_secs'],"end_secs":after['end_secs']}},w=1)
        results = conn.find().sort("_id",pymongo.ASCENDING)
        for result in results:
            result['start_date'] = datetime.datetime.fromtimestamp(result['start_secs']).strftime('%Y-%m-%d')
            result['end_date'] = datetime.datetime.fromtimestamp(result['end_secs']).strftime('%Y-%m-%d')
            conn.update({"_id":result['_id']},{'$set':{"start_date":result['start_date'],"end_date":result['end_date']}})
    
    def save(self, period_id, stage,children_json):
        flag = True
        try:
            children = ujson.loads(children_json)
            key_fmt = "children.%s.day"
            field = {}
            for child in children:
                child_id = int(child['child_id'])
                child_day = int(child['child_day'])
                field[key_fmt % child_id] = child_day
            conn = DBConnPool.get_collection(DB_NAME,"plan")
            print period_id,field
            conn.update({"id":period_id},{"$set":field},upsert=True)
            self.init_trans_data_with_finish_date()
        except Exception as ex:
            flag = False
            # self._logger.error("save occur exception due to: %s",ex)
        return flag
    
    def generate_excel(self):
        flag = True
        filename = '/static/resp/设计计划日程表.xlsx'
        try:
            conn = DBConnPool.get_collection(DB_NAME, "plan")
            plan_excel = xlsxwriter.Workbook(os.getcwd()+filename)
            worksheet = plan_excel.add_worksheet('计划日程表1')
            stages = conn.distinct("stage")
            base_offset = 4
            init_pos = (0,0)
            # print os.getcwd()+'static/resp/plan_schedule.xlsx'
            results = conn.find({}).sort("id", pymongo.ASCENDING)
            title_pos = init_pos
            title_fomat = plan_excel.add_format({
                'align' : 'center',
                'bold' : True,
                'valign' : 'vcenter',
            })
            for stage in stages:
                parentname = None
                results = conn.find({"stage":stage}).sort("_id",pymongo.ASCENDING)
                for result in results:
                    parentname = result['parentname']
            for result in results:
#                 children = result['children']
                child_name = result['name']
                child_day = result['day']
                child_start = result['start_date']
                child_end = result['end_date']
                
#             for k in sorted(children.keys()):
#                 v = children[k]
#                 child_name = v['name']
#                 child_day = v['day']
#                 child_finish = datetime.datetime.fromtimestamp(v['finishtime']).strftime("%Y-%m-%d")

                name_f = init_pos
                name_l = name_f[0]+xls_name-1, name_f[1]+base_offset-1
                # print name_f
                # print name_l
                child_name_f = name_l[0]+1, name_f[1]
                child_name_l = child_name_f[0]+xls_child_name-1, child_name_f[1]+base_offset-1
                # print child_name_f
                # print child_name_l
                child_day_f = child_name_l[0]+1, child_name_f[1]
                child_day_l = child_day_f[0]+xls_child_day-1, child_day_f[1]+base_offset-1
                # print child_day_f
                # print child_day_l
                # worksheet.merge_range(name_f[1], name_f[0], name_l[1], name_l[0],result['name'])
                child_start_f = child_day_l[0]+1, child_day_f[1]
                child_start_l = child_start_f[0]+xls_child_finish-1, child_start_f[1]+base_offset-1
                
                child_end_f = child_start_f[0]+1, child_start_f[1]
                child_end_l = child_end_f[0]+xls_child_finish-1, child_end_f[1]+base_offset-1

                worksheet.merge_range(child_name_f[1], child_name_f[0], child_name_l[1], child_name_l[0],child_name,title_fomat)
                worksheet.merge_range(child_day_f[1], child_day_f[0], child_day_l[1], child_day_l[0],"工期约"+str(child_day)+"天",title_fomat)
                worksheet.merge_range(child_start_f[1], child_start_f[0], child_start_l[1], child_start_l[0],"预计在"+str(child_start)+"日开始",title_fomat)
                worksheet.merge_range(child_end_f[1], child_end_f[0], child_end_l[1], child_end_l[0],"预计在"+str(child_end)+"日完工",title_fomat)
                init_pos = init_pos[0],init_pos[1]+base_offset
            worksheet.merge_range(title_pos[1],title_pos[0],init_pos[1]-1,xls_name-1,result['name'],title_fomat)
            title_pos = title_pos[0], title_pos[1]+base_offset*len(results)
            plan_excel.close()
        except Exception as ex:
            flag = False
        return {"success":flag,"filename":filename}