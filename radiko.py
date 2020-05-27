#-*- coding: utf-8 -*-

import os
import time
import datetime
import base64
import requests
import xml.etree.ElementTree as ET

# Radiko 処理

# Radikoプレミアム時にCookieを保存するパス
radiko_cookie_path ='./'
# RadikoプレミアムのCokkie寿命(とりあえず1ヵ月)
radiko_cookie_expires = (30*24*60*60)

# Radiikoプレミアムログイン
# returnはcokkieかFalse
def radiko_p_login(r_user="", r_pass="") :

    # プレミアム用cookie
    radiko_cookie = {}

    #print("## プレミアムログイン ##")

    if r_user != "" and r_pass != "":

        #保存済のCookieがあるかどうかをチェック
        saved_cookie = "%s/radiko.cookie" % radiko_cookie_path
        if os.path.isfile(saved_cookie):
            with open('radiko.cookie', 'r') as f:
                tstamp = f.readline().rstrip('\n')
                r_session = f.readline().rstrip('\n')
                s_token = f.readline().rstrip('\n')
            tstamp = tstamp.split(':',2)[1]
            r_session = r_session.split(':',2)[1]
            s_token = s_token.split(':',2)[1]
            now_ut = time.time()
            ts_delta = float(now_ut) - float(tstamp)
            #print('Cookie Delta : %f' % ts_delta)
            if ts_delta < radiko_cookie_expires: #寿命内に保存されていたのでOK
                #Cookieを作成
                radiko_cookie = {
                    'radiko_session': r_session,
                    'ssl_token' : s_token
                }

                #print('保存済Cookieが有効')
                return(radiko_cookie)

        # Cookieが無いか古いので再度ログイン

        sess = requests.session()

        headers = {
            'User-Agent': 'radiko/0.0.1',
            'Accept': '*/*',
            'x-radiko-app': 'pc_html5',
            'x-radiko-app-version': '0.0.1',
            'x-radiko-device': 'pc'
        }

        # ログインデータとしてユーザ名とパスワードをセット
        logindata = {'mail': r_user, 'pass': r_pass}

        # セッションをオープン
        #print('Cookie取得ログイン')
        res = sess.post('https://radiko.jp/ap/member/login/login',headers=headers, data=logindata)
        #print(res)

        # Status OKでなければ継続しない
        if res.status_code != 200:
            return(False)

        #print(requests.utils.dict_from_cookiejar(sess.cookies))
        #print(sess.cookies.keys)

        radiko_session_cookie = sess.cookies.get('radiko_session')
        radiko_session_ssl_token = sess.cookies.get('ssl_token')
        #print(radiko_session_cookie)
        #print(radiko_session_ssl_token)

        # 現在のタイムスタンプとCokieを保存
        now_ut = time.time()
        with open(saved_cookie, 'w') as f:
            f.write("timestamp:%s" % now_ut)
            f.write("\n")
            f.write("radiko_session:%s" % radiko_session_cookie)
            f.write("\n")
            f.write("ssl_token:%s" % radiko_session_ssl_token)
            f.write("\n")

        radiko_cookie = {
            'radiko_session': radiko_session_cookie,
            'ssl_token' : radiko_session_ssl_token
        }
        return(radiko_cookie)
    else:
        #print('### プレミアムではない ###')
        return(False)

    return(False)

# 再生情報取得
def get_radiko_info(station, r_user="", r_pass=""):

    # キーは今のところ固定らしいので
    fixed_key = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"

    # プレミアム用cookie
    radiko_cookie = {}


    # 引数チェック:引数はRadikoの局名
    # ユーザ名とパスワードがない場合にはNotプレミアム
    if station == "":
         return(False)

    radiko_user = r_user
    radiko_pass = r_pass

    #ユーザが設定されていないのにcookieがある場合には削除
    saved_cookie = "%s/radiko.cookie" % radiko_cookie_path
    if radiko_user == "":
        if os.path.isfile(saved_cookie):
            os.remove(saved_cookie)


    ####
    #print("## プレミアムログイン ##")
    if radiko_user != "" and radiko_pass != "":
        ret = radiko_p_login(radiko_user, radiko_pass)
        if ret != False:
            radiko_cookie = ret


    ####
    #print("## 認証ステップ1 ##")

    headers = {
        'User-Agent': 'radiko/0.0.1',
        'Accept': '*/*',
        'x-radiko-user': 'dummy_user',
        'x-radiko-app': 'pc_html5',
        'x-radiko-app-version': '0.0.1',
        'x-radiko-device': 'pc'
    }

    # GETリクエストして認証(1)
    res1 = requests.get('https://radiko.jp/v2/api/auth1', headers=headers, cookies=radiko_cookie)

    # Status OKでなければ継続しない
    if res1.status_code != 200:
        return(False)

    # ヘッダから各キーを変数にセット
    key_len = int(res1.headers['X-Radiko-KeyLength'])
    key_offset = int(res1.headers['X-Radiko-KeyOffset'])
    radiko_authtoken = res1.headers['X-Radiko-AUTHTOKEN']

    #print(res1)
    #print(key_len)
    #print(key_offset)
    #print(radiko_authtoken)


    # パーシャルキーをつくる
    fixed_key_b = fixed_key.encode('utf-8')
    partial_key_b = base64.b64encode(fixed_key_b[key_offset: key_offset + key_len])
    partial_key = partial_key_b.decode('utf-8')

    #print(partial_key)

    ####
    #print("## 認証ステップ2 ##")

    headers = {
        'User-Agent': 'curl/7.52.1',
        'Accept': '*/*',
        'x-radiko-user': 'dummy_user',
        'X-RADIKO-AUTHTOKEN': radiko_authtoken,
        'x-radiko-partialkey': partial_key,
        'x-radiko-device': 'pc'
    }

    # パーシャルキーを使って認証(2)
    res2 = requests.get('https://radiko.jp/v2/api/auth2', headers=headers, cookies=radiko_cookie)

    #print(res2)

    # Status OKでなければ継続しない
    if res2.status_code != 200:
        return(False)

    ####
    #print("## 再生URL取得 ##")

    # 認証が完了したので再生URLを取得
    # f-radikoとc-radikoの2種類があるらしいのでXMLから取得してみる
    req_url = "http://radiko.jp/v2/station/stream_smh_multi/%s.xml" % station
    res3 = requests.get(req_url, headers=headers, cookies=radiko_cookie)

    # Status OKでなければ継続しない
    #print(res3)
    if res3.status_code != 200:
        return()

    # 取得したXMLからターゲットURLを取り出し
    station_xml = ET.fromstring(res3.content)
    #print(station_xml)
    try_url = station_xml[0][1].text
    #print(try_url)

    headers = {
        'X-RADIKO-AUTHTOKEN': radiko_authtoken
    }


    # ターゲットURLから実際の再生URLを取得
    res4 = requests.get(try_url, headers=headers)
    #print(res4)

    # Status OKでなければ継続しない
    if res4.status_code != 200:
        return(False)

    # 実際の再生URLを取り出し
    stream_url = res4.content.splitlines()[-1]
    stream_url = stream_url.decode('utf-8')
    #print(stream_url)

    retval = (radiko_authtoken, stream_url)

    return(retval)
