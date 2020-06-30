#-*- coding:utf-8 -*-

# サイマルラジオ(www.simulradio.info) 及び ASX再生対応
import requests

# ASXからターゲットのURL(http:またはmms:)を求める
def asx_to_target(url=''):

    if url != '':
        res = requests.get(url)
        if res.status_code != 200:
            return False

        content = res.text.splitlines()

        http_target = ''
        mms_target = ''

        for line in  content:
            if 'Ref href' in line or 'ref href' in line:
                 tmp_line = line.split('"')[1]
                 if 'http:' in tmp_line or 'https:' in tmp_line:
                     http_target = tmp_line
                 if 'mms:' in tmp_line:
                     mms_target = tmp_line 

        if mms_target != '':
            return(mms_target)
        elif http_target != '':
            return(http_target)
        else:
            return(False)

    return(False) 

# サイマルラジオの再生URLを求める(単なるラッパー)
# ASXで再生される場合にURLを省略するために使う
# www.simulradio.info/asx/[ここが局名].asx
def get_simulradio_url(station=''):

    if station != '' :
        simul_url = 'http://www.simulradio.info/asx/%s.asx' % station 
        ret = asx_to_target(simul_url)
        return(ret)

    return(False)
