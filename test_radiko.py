#-*- coding: utf-8 -*-

# Radiko再生テスト用プログラム

import sys
import signal
import time
import datetime
import os
import subprocess
import threading
import radiko

# オーディオデバイスはここで指定する
radio_audio_driver = 'alsa'
#radio_audio_device = 'plughw:0'
radio_audio_device = 'plughw:1'

# Radiko再生
def play_radiko(station, r_user="", r_pass=""):

    # Radikoの再生情報を取得
    ret = radiko.get_radiko_info(station,r_user,r_pass)
    if ret != False:
        (authtoken, streamurl) = ret

        radiko_cmd = "ffplay -vn -headers \"X-RADIKO-AUTHTOKEN: {0}\" -i {1}".format(authtoken, streamurl)
        print(radiko_cmd)

        try:
            radio_audio_driver
            os.putenv('SDL_AUDIODRIVER', radio_audio_driver)
        except:
            pass
        try:
            radio_audio_device
            os.putenv('AUDIODEV', radio_audio_device)
        except:
            pass
        os.system(radiko_cmd)
        return()

    return()

#
#####
#
if __name__ == "__main__":
    # Radikoの識別名を指定して再生をテスト
    # エリアに依存しないラジオ日経1,2あたりが便利(RN1,RN2) ただし運用時間注意 
    # エリアに依存しない局としてはNHK-FM(JOAK-FM)も便利
    play_radiko('JOAK-FM')
