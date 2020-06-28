#-*- coding: utf-8 -*-

import os
import time
import datetime
import base64
import requests
import xml.etree.ElementTree as ET

def radiru_url(radio_id=''):
    #print("## らじる再生URL取得 ##")

    try:
        r_area = radio_id.split('-')[0]
        r_station = radio_id.split('-')[1] + 'hls'
    except:
        return(False)

    #print(r_area, r_station)

    req_url = "https://www.nhk.or.jp/radio/config/config_web.xml"
    res = requests.get(req_url)

    # Status OKでなければ継続しない
    #print(res)
    if res.status_code != 200:
        return(False)

    # 取得したXMLからターゲットURLを取り出し
    station_xml = ET.fromstring(res.content)
    for r_data in station_xml.iter(tag='data'):
        r1hls = ''
        r2hls = ''
        fmhls = ''
        area_matched = 0
        for r_elem in r_data.iter():
            if r_elem.tag == 'area':
                if r_elem.text == r_area:
                    area_matched = 1
            if area_matched == 1:
                if r_elem.tag == r_station:
                    r_url = r_elem.text
                    return(r_url) 
    return(False)
