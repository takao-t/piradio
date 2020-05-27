#-*- coding: utf-8 -*-

# Radiko放送局一覧を取得する
# 使い方
# python ./get_stations.py > 保存先
# python ./get_stations.py >> 保存先 で追加してもよし
# 各局のロゴファイルは自動ダウンロードされる
# なお、ラジオ日経など全国放送は重複するので手動編集してください
# エリアフリーを使用している場合の県外局はコードを指定して取得
# python ./get_stations.py JP1 > 保存先
# JP1は都道府県コード(例:JP1-北海道, JP47-沖縄県)

import time
import base64
import requests
import os
import sys
import xml.etree.ElementTree as ET
import datetime
import time
import codecs


# Radikoエリアチェック
def check_radiko_area():

    headers = {
        'User-Agent': 'radiko/0.0.1',
        'Accept': '*/*',
        'x-radiko-user': 'dummy_user',
        'x-radiko-app': 'pc_html5',
        'x-radiko-app-version': '0.0.1',
        'x-radiko-device': 'pc'
    }

    # GETリクエストしてエリアコード取得
    res1 = requests.get('https://radiko.jp/area')

    # Status OKでなければ継続しない
    if res1.status_code != 200:
        return()

    area_code = res1.text.split('class=',1)[1]
    area_code = area_code.split('>',1)[0]
    area_code = area_code.replace('"', '')

    area_name = res1.text.split('>',1)[1]
    area_name = area_name.split('<',1)[0]

    #print(u"現在のエリア : %s    コード : %s" % (area_name, area_code))

    return(area_code)


def get_stations(area_code):
    station_url = 'https://radiko.jp/v2/station/list/%s.xml' % area_code

    res2 = requests.get(station_url)

    radiko_xml = ET.fromstring(res2.content)

    root = radiko_xml

    for station in  root.findall('station'):
        station_id = station.find('id').text
        station_name = station.find('name').text
        station_aname = station.find('ascii_name').text
        station_logo = station.find('logo_xsmall').text
        logo_data = requests.get(station_logo)
        if logo_data.status_code == 200:
            logo_file_name = "%s.png" % station_id
            with open(logo_file_name, 'wb') as f:
                f.write(logo_data.content)
        else:
            logo_file_name = ""
        station_info = "%s,%s,%s,%s,radiko" % (station_id, station_name, station_aname, logo_file_name)
        print(station_info)

if __name__ == "__main__":
    args = sys.argv

    sys.stdin  = codecs.getreader('utf-8')(sys.stdin)
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

    if len(args) == 1:
        ac = check_radiko_area()
        get_stations(ac)
    else:
        get_stations(args[1])
