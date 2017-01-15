from common.database import MongoAccount, DBConnPool
from conf.settings import DATABASE_TV, DB_NAME
from flask import Flask, request
from flask.templating import render_template
from handler.bidhandler import BidHandler
from handler.planhandler import PlanHandler
import pymongo
import ujson



app = Flask(__name__)


# @app.route('/')
# def hello_world():
#     return 'Hello World!'

def _load_bid_users():
        conn = DBConnPool.get_collection(DB_NAME, "bid_user")
        users = conn.find().sort("_id",pymongo.ASCENDING)
        return users

@app.route('/')
def plan():
    return render_template('plan.html')

@app.route("/plan/init")
def init_plan():
    PlanHandler().init_trans_data()
    return ujson.dumps({"success":True,"message":"init success"},ensure_ascii=False)

@app.route("/bid/plan_init")
def init_bid_plan():
    BidHandler().init_bid_data()
    return ujson.dumps({"success":True,"message":"init success"},ensure_ascii=False)

@app.route("/bid/plan/<int:bidid>/<int:rank>")
def bid_plan_stage(bidid=1,rank=1):
#     planinfos,total = PlanHandler().plan_by_rank(rank)
#     return render_template('bid_plan.html',rank=rank,planinfos = planinfos,total=total)
    orplaninfo = {}
    planinfos,total,bidview = BidHandler().plan_by_rank_and_bid(bidid, rank)
    if planinfos:
        orplaninfo = PlanHandler().plan_by_id(planinfos[0]['id'])
#     base_info = PlanHandler().get_base_information()
    return render_template('bid_plan.html',bidid=bidid,rank=rank,planinfos = planinfos,total=total,orplaninfo=orplaninfo,bid_users=_load_bid_users(),bidview=bidview)


@app.route('/plan/save2',methods=['GET','POST'])
def plan_init():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    id = int(request.form.get('id'))
    rank = int(request.form.get('rank'))
    PlanHandler().init_trans_data_with_date(id,start_date,end_date,rank)
    planinfos,total = PlanHandler().plan_by_rank(rank)
#     stageinfos = PlanHandler().plan_by_rank(rank)
#     base_info = PlanHandler().get_base_information()
    return render_template('plan.html',rank=rank,planinfos = planinfos,total=total)

@app.route('/bid/plan/save',methods=['GET','POST'])
def bid_plan_save():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    bidid = int(request.form.get('bidid'))
    id = int(request.form.get('id'))
    rank = int(request.form.get('rank'))
    BidHandler().plan_save_by_rank_and_bid(start_date,end_date,bidid,id,rank)
    orplaninfo = {}
#     planinfos,total = BidHandler().plan_by_rank_and_bid(bidid, rank)
    planinfos,total,bidview = BidHandler().plan_by_rank_and_bid(bidid, rank)
    if planinfos:
        orplaninfo = PlanHandler().plan_by_id(planinfos[0]['id'])
#     base_info = PlanHandler().get_base_information()
    return render_template('bid_plan.html',bidid=bidid,rank=rank,planinfos = planinfos,total=total,orplaninfo=orplaninfo,bid_users=_load_bid_users(),bidview=bidview)
    
#     PlanHandler().init_trans_data_with_date(id,start_date,end_date,rank)
#     planinfos,total = PlanHandler().plan_by_rank(rank)
#     stageinfos = PlanHandler().plan_by_rank(rank)
#     base_info = PlanHandler().get_base_information()
#     return render_template('plan.html',rank=rank,planinfos = planinfos,total=total)

@app.route('/plan')
@app.route('/plan/<int:rank>')
def plan_stage(rank=1):
    planinfos,total = PlanHandler().plan_by_rank(rank)
#     base_info = PlanHandler().get_base_information()
    return render_template('plan.html',rank=rank,planinfos = planinfos,total=total)

@app.route('/plan/save', methods=['GET', 'POST'])
def plan_save():
    period_id = request.form.get('period_id')
    stage = request.form.get('stage')
    children = request.form.get('children')
    flag = PlanHandler().save(int(period_id), stage, children)
    return ujson.dumps({"success": flag}, ensure_ascii=False)

def init_connection_pool():
    
    account = MongoAccount(DATABASE_TV["db_user"],
                           DATABASE_TV["db_pass"],
                           DATABASE_TV["db_sock"],
                           DATABASE_TV["db_size"])
    DBConnPool.connect(account)

if __name__ == '__main__':
    init_connection_pool()
    app.run(host="0.0.0.0",port=9000,debug=True,use_reloader=False)
