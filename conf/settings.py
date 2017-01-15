# -*- coding: utf-8 -*-
# 文件名: settings.py
# 摘  要: 系统相关配置

LOCAL_HOST_NAME = "localhost"
DB_NAME = "transcms"

MONGODBLIST = [
#     '114.112.81.18:27017'
    'localhost:27017'
#     '114.112.81.25:27071'
]

DATABASE_TV = {
    'db_size' : 10,
#     'db_user' : 'admin',
#     'db_pass' : 'dKdb#2011',
    'db_user':'',
    'db_pass':'',
    'db_sock' : ','.join(MONGODBLIST), 
}



WEB_SERVER_CONFIG = {
    "domain":'http://duokantv.com/',
    "static_file_server": "http://tvcdn.duokan.com/",
    "xiaomi_file_server": "http://file.market.xiaomi.com/download/",
    "cntv_cdn_file_server":"http://cntv.cdn.duokan.com/rom/",
    "api_token" : "0f9dfa001cba164d7bda671649c50abf",
    "api_secret_key" : "581582928c881b42eedce96331bff5d3",
    "max_time_delta" : 60, #maximum time delta between client and server
    "active_token": "7a3689fa91bc4693a658db0d08aa780f",
    "active_key": "a2f571c79d0c4867992ab53cafa7e623",    
    "sohu_m3u8_path_prefix": 'sohu',
    "youku_m3u8_pattern" : '%s/type/%s/video.m3u8',
    "video_addr_proxy" : 'http://114.112.81.22:8882/',
    "proxy_name": 'dkproxy         ',
    "proxy_password": 'E3aX0tjU        '
}
