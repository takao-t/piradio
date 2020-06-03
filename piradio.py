#-*- coding: utf-8 -*-

# Raspberry Piをradikoラジオにする
# Python 2.7 対応 (3は一部書き換えて)
#
# 要るもの:
# Raspberri Pi 3とか4とかZero Wとか
# GPIOに繋ぐスイッチ5個
# フレームバッファ(/dev/fbX)として使える液晶
# このスクリプトでは320x240を想定
# 画面にはpygameを使用
# 要するにpygameで表示できればOK
# 日本語表示用の適当なTTFフォント(フォントがないと止まるので注意)
# このソース内をfont1で検索して書き換え位置を探して
# ffmpeg(ffplay)

import sys
import signal
import time
import datetime
import os
import subprocess
import threading

# Python2
import SocketServer
# Python3
#import socketserver as SocketServer

import RPi.GPIO as GPIO
import base64
import requests
import xml.etree.ElementTree as ET
import codecs
# Radiko処理用
import radiko

# 引数処理
if "-nogui" in sys.argv:
    try:
        use_gui
        del use_gui
    except:
        pass
    print("No GUI mode")
else:
    use_gui = 1
    print("GUI mode(default)")


try:
    use_gui
    import pygame
    from pygame.locals import *
except:
    pass

# システム設定
# 
# オーディオ関連の設定は alsa_README.txt も参照のこと
#  オーディオドライバ
radio_audio_driver = 'alsa'
#  出力デバイス
#radio_audio_device = 'plughw:CARD=Device,DEV=0'
#radio_audio_device = 'plughw:CARD=ALSA,DEV=0'
radio_audio_device = 'plughw:0'
#radio_audio_device = 'plughw:1'
# 音量調整デバイス(amixerの引数: -c0 -c1など)
#radio_volume_device = '-c1'
radio_volume_device = '-c0'
# 音量調整コントローラ名
#radio_volume_ctl = 'PCM'
radio_volume_ctl = 'Headphone'
# APIのポート(APIを使用しない場合はコメントアウト)
piradio_api_port = 8899

# Radikoプレミアムでエリアフリーを使う場合には設定する
radiko_user = ''
radiko_pass = ''

# 局設定リストのファイル
station_file = 'stations/station_list'
# ロゴファイルのパス
station_logo_path = 'stations/'

# 320x240のディスプレイを使用
# pygameで使用するフレームバッファだけあればOK
os.putenv('SDL_FBDEV', '/dev/fb1')

# 制御用スイッチ:GPIO番号(BCM)
# 注: 使用しないスイッチはコメントアウトして変数をセットしない
#     例えばTUNE_DOWNを指定しなければ合計4ボタンで実装できる
#     音量調整しない場合なら最低2ボタンでも可能
#     ただし再生停止ボタンは必須
# スイッチを接続したGPIO番号に書き換える
class CTRL_SW:
    STARTSTOP = 18
    TUNE_UP = 27
    TUNE_DOWN = 22
    VOLUME_UP = 21
    VOLUME_DOWN = 23

# 音量(初期値)
vol_val = 8

# 画面背景色
sc_bg_color = (0,128,128)
# 選択項目表示色
#b_bright = (150,50,20)
b_bright = (255,255,255)
# 暗表示色
#b_dark = (96,96,96)
b_dark = (128,128,128)
# 局名テキスト表示色
#st_text_color = (180, 180, 180)
st_text_color = (0, 0, 0)
# 画面下小文字表示色
bt_text_color = (0,255,0)

# 局名表示横幅
station_disp_x = 320
# 局名表示縦幅
station_disp_y = 36 
# 局名表示文字位置オフセット
text_offset_x = 110
text_offset_y = 2
#text_offset_y = 0


#####
# 局の選択位置
p_selected = 0
# 前回の選択局
p_last_selected = 0
# 1ページあたり局数
station_per_page = 6
# 選択して実行しない時間カウンタ
p_nexec_count = 0
# 実行しないで放置と判断するまでのタイムアウト
p_nexec_timeout = 10

# 音量調整用プロファイル(32段階)
volume_profile = [ 0, 6, 9,12,15,18,21,24,27,30,33,36,39,42,45,48, \
                  51,54,57,60,63,66,69,72,75,78,81,84,87,90,93,96 ]

# GPIOの問題避け
prev_pushed_time = 0

# 再生停止コマンド
stop_play_cmd = 'killall ffplay'

# 局名リスト読み込み処理
station_lists = []
# For Python2
with codecs.open(station_file, 'r', 'utf-8') as f:
# For Python3
#with open(station_file, 'r', encoding='utf-8') as f:
    s_line = f.readline()
    while s_line:
        station_id = s_line.split(',',5)[0]
        station_name = s_line.split(',',5)[1]
        station_aname = s_line.split(',',5)[2]
        station_logo = s_line.split(',',5)[3]
        p_method = s_line.split(',',5)[4]
        p_method = p_method.strip()
        #print("%s : %s : %s : %s : %s" % (station_id, station_name, station_aname, station_logo,p_method))
        station_lists.append( [station_id,station_name,station_aname,station_logo,p_method] )
        s_line = f.readline()

#局数
num_stations = len(station_lists)
#print(num_stations)

try:
    use_gui
    # pygame初期化
    pygame.init()
    screen = pygame.display.set_mode((320, 240))
    pygame.mouse.set_visible(False)

    #背景色
    screen.fill(sc_bg_color)
    pygame.display.update()

    # フォント
    # フォントはスクリプトが読めるところに置いたTTFフォント
    # 画面上の局名表示用
    #font1 = pygame.font.Font("ipaexg.ttf", 24)
    #font1 = pygame.font.Font("azukiLB.ttf", 24)
    #font1 = pygame.font.Font("TanukiMagic.ttf", 24)
    font1 = pygame.font.Font("mplus-1p-medium.ttf", 20)
    # 音量表示用
    font2 = pygame.font.SysFont(None, 128)
    # "WAIT"表示用
    font3 = pygame.font.SysFont(None, 64)
    # ミニフォント(画面下部表示用)
    font4 = pygame.font.SysFont(None, 22)

    #表示局名生成
    texts = []
    for tmp_pos in range(num_stations):
        (dummy1, station_text, dummy2, dummy3, dummy4) = station_lists[tmp_pos]
        if station_text == "":
            station_text = "  "
        texts.append( font1.render(station_text, True, st_text_color) )

    # 局名背景表示
    station_bg = []
    station_bg.append( pygame.Rect(0, 0, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, station_disp_y+2, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*2, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*3, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*4, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*5, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*6, station_disp_x, station_disp_y) )
    station_bg.append( pygame.Rect(0, (station_disp_y+2)*7, station_disp_x, station_disp_y) )
except:
    pass

#####
#外部コントロール用APIハンドラ
#コマンド
# START:stioinid
# STOP:
class APIHandler(SocketServer.BaseRequestHandler):

    def handle(self):

        global station_lists
        global p_selected

        self.data = self.request.recv(256).strip()

        cmd = self.data.split(b':',2)[0]
        cmd = cmd.decode('utf-8')
        target = self.data.split(b':',2)[1]
        target = target.decode('utf-8')
        print(cmd)
        print(target)

        if cmd == 'START':
            #print('START commdan for %s' % target)
            sl_len = len(station_lists)
            #print(sl_len)
            for tmp_pos in range(sl_len):
                (id, name, aname, logo, method) = station_lists[tmp_pos]
                if id == target:
                    #print(station_lists[tmp_pos])
                    self.request.sendall("OK\n".encode('utf-8'))
                    p_selected = tmp_pos
                    api_p_start()
                    return(True)
            self.request.sendall("NOMATCH\n".encode('utf-8'))
            return(False)
        if cmd == 'STOP':
            #print('STOP')
            api_p_stop()
            self.request.sendall("OK\n".encode('utf-8'))
            return(True)

        self.request.sendall("ERR\n".encode('utf-8'))
        return(False)

# API用スレッド
def api_server_th():
    api_server.serve_forever()

# API起動
try:
    piradio_api_port
    api_server = SocketServer.ThreadingTCPServer(("localhost", piradio_api_port), APIHandler)
    apit = threading.Thread(target=api_server_th)
    apit.start()
except:
    pass

# APIからの再生処理
def api_p_start():
    global p_selected
    global p_last_selected
    global stop_play_cmd
    # 再生開始のWAITの表示
    popup_text('WAIT',(255,174,0))
    # 再生を強制停止
    os.system(stop_play_cmd)
    time.sleep(0.5)
    station_num = p_selected
    (station_id, dummy1, dummy2, dummy3, p_method) = station_lists[station_num]
    # 再生方法がRadiko
    if p_method == 'radiko':
        stop_play_cmd = 'killall ffplay'
        play_radiko(station_id,radiko_user,radiko_pass)
    # 再生方法がらじる
    if p_method == 'radiru':
        stop_play_cmd = 'killall ffplay'
        play_radiru(station_id)
    #
    p_last_selected = p_selected
    p_nexec_count = 0
    # WAIT表示のままちょいまち
    time.sleep(3)
    disp_update()
    print("API-PLAY : %s" % station_id)

# APIからの停止処理
def api_p_stop():
    global stop_play_cmd
    # 再生ストップの表示
    popup_text('STOP',(255,0,0))
    # 再生を停止
    os.system(stop_play_cmd)
    time.sleep(0.5)
    disp_update()
    print("API-STOP")


# シグナルハンドラ(終了処理)
def signal_handler(signal,stack):
    global stop_play_cmd
    print('Got signal: Quiting...')
    api_server.shutdown()
    os.system(stop_play_cmd)
    time.sleep(1)
    try:
        use_gui
        pygame.quit()
    except:
        pass
    GPIO.cleanup()
    sys.exit()

# 再生/停止
def p_startstop(pinnum):
    #print(pinnum)

    global p_selected
    global p_last_selected
    global p_nexec_count
    global p_nexec_timeout
    global stop_play_cmd

    # GPIO割込みが2重検出される問題避け
    # 他のスイッチではあまり問題ではないがSTART/STOPだけは大問題なのでworkaround
    global prev_pushed_time
    # ガードタイムはこの処理(0.5+3) +0.5で設定
    guard_time = 4

    # GPIO割込みの2重検出避け
    pushed_time = time.time()
    if (pushed_time - prev_pushed_time) < guard_time:
        return()
    prev_pushed_time = time.time()

    try:
        res = subprocess.check_output(["pgrep","ffplay"])
        # 再生ストップスタートのWAIT表示
        popup_text('STOP',(255,0,0))
        # 再生を停止
        os.system(stop_play_cmd)
        time.sleep(0.5)
        do_pb = 0
        # 選局操作を行った後なら再度再生実行
        if p_selected != p_last_selected:
             do_pb = 1
    except:
        # 現在再生されていないので再生実行
        do_pb = 1

    if do_pb == 1:

        # 再生ストップスタートのWAIT表示
        disp_update()
        popup_text('WAIT',(0,255,0))

        station_num = p_selected 
        (station_id, dummy1, dummy2, dummy3, p_method) = station_lists[station_num]
        #print(station_id)
        #print(p_method)
        # 再生方法によって処理をわける(局リストのp_method)。他の方法で再生したければここに書く
        # 再生方法がRadiko
        if p_method == 'radiko':
            stop_play_cmd = 'killall ffplay'
            play_radiko(station_id,radiko_user,radiko_pass)
        # 再生方法がらじる
        if p_method == 'radiru':
            stop_play_cmd = 'killall ffplay'
            play_radiru(station_id)
        #
        p_last_selected = p_selected
        p_nexec_count = 0
        # WAIT表示のままちょいまち
        time.sleep(3)

    #元画面再表示
    disp_update()

# 選局
def p_tunectl(pinnum):
    #print(pinnum)

    global p_selected
    global p_nexec_count

    try:
        CTRL_SW.TUNE_UP
        if pinnum == CTRL_SW.TUNE_UP:
            p_nexec_count = p_nexec_timeout
            p_selected += 1
            if p_selected >= num_stations:
                p_selected = 0
    except:
        pass

    try:
        CTRL_SW.TUNE_DOWN
        if pinnum == CTRL_SW.TUNE_DOWN:
            p_nexec_count = p_nexec_timeout
            p_selected -= 1
            if p_selected < 0:
                p_selected = num_stations -1
    except:
        pass

    #print(p_selected)
    disp_update()

# 音量
def p_volumectl(pinnum):
    #print(pinnum)

    global vol_val

    try:
        CTRL_SW.VOLUME_UP
        if pinnum == CTRL_SW.VOLUME_UP:
            vol_val += 1
            if vol_val >= 31:
                vol_val = 31 
            vol_target = volume_profile[vol_val]
            vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (radio_volume_device, radio_volume_ctl, vol_target, vol_target)
            os.system(vol_cmd)
    except:
        pass
    try:
        CTRL_SW.VOLUME_DOWN
        if pinnum == CTRL_SW.VOLUME_DOWN:
            vol_val -= 1
            if vol_val <= 0:
                vol_val = 0
            vol_target = volume_profile[vol_val]
            vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (radio_volume_device, radio_volume_ctl, vol_target, vol_target)
            os.system(vol_cmd)
    except:
        pass

    disp_update()
    #print(vol_target)

# 画面表示更新
def disp_update():

    global p_selected

    try:
        use_gui
        #print(p_selected)

        screen.fill(sc_bg_color)

        dsp_page = int(p_selected / station_per_page) * station_per_page
        dsp_pos = p_selected - dsp_page

        b_count = 0
        text_org_x = text_offset_x
        text_org_y = text_offset_y

        ta_len = len(texts)

        b_pos = 0
        for b_pos in range(station_per_page):
            if dsp_pos == b_pos:
                b_brightness = b_bright
            else:
                b_brightness = b_dark
            pygame.draw.rect(screen, b_brightness, station_bg[b_pos])
            #ページ内の表示局数が下までない場合にはテキストを書かない(書けない)
            if (b_pos+dsp_page) < ta_len:
                screen.blit(texts[b_pos+dsp_page], (text_org_x,text_org_y))
                # 局名ロゴ表示
                (dummmy1,dummy2,dummy3,station_logo,dummy4) = station_lists[b_pos+dsp_page]
                if station_logo != "":
                    try:
                        station_icon = pygame.image.load("%s/%s" % (station_logo_path,station_logo) )
                        screen.blit(station_icon,(0,text_org_y-text_offset_y))
                    except:
                        pass
            text_org_y += (station_disp_y + 2)

            b_count += 1

        #画面下音量表示
        stay_voltext = font4.render(str(('VOL: %d' % vol_val)), True, bt_text_color)
        screen.blit(stay_voltext, (20,226))
        #画面下日付時刻
        disp_datetime()

        pygame.display.update()
    except:
        pass

# 画面右下日時表示更新
def disp_datetime():
    try:
        use_gui
        # 背景をfillしなおさないので表示位置だけ消去するためrectを書く
        pygame.draw.rect(screen, sc_bg_color, (110,226,319,240) )
        now_dt = datetime.datetime.now()
        now_str = now_dt.strftime('%Y/%m/%d %a  %H:%M')
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            cpu_t = f.read()
        cpu_t = round(float(cpu_t) / 1000.0) 
        ctt = "%d'C" % cpu_t
        now_str = ctt + '    ' + now_str
        now_text = font4.render(str(now_str), True, bt_text_color)
        screen.blit(now_text, (110,226))
        pygame.display.update()
    except:
        pass


# 画面上ポップアップテキスト
def popup_text(text,color):
    try:
        use_gui
        waittext = font3.render(text, True, color)
        screen.blit(waittext, (100,70))
        pygame.display.update()
    except:
        pass

# メイン処理
def main():

    global p_nexec_count
    global p_selected
    global p_last_selected

    # シグナル(HUP,INT,QUITで終了)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    # GPIOセットアップ
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    # 各ピンを入力,プルアップありにしピンの割り込みハンドラを設定
    try:
        CTRL_SW.STARTSTOP
        GPIO.setup(CTRL_SW.STARTSTOP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.STARTSTOP, GPIO.FALLING, callback=p_startstop, bouncetime=500)
    except:
        pass
    try:
        CTRL_SW.TUNE_UP
        GPIO.setup(CTRL_SW.TUNE_UP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.TUNE_UP, GPIO.FALLING, callback=p_tunectl, bouncetime=300)
    except:
        pass
    try:
        CTRL_SW.TUNE_DOWN
        GPIO.setup(CTRL_SW.TUNE_DOWN,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.TUNE_DOWN, GPIO.FALLING, callback=p_tunectl, bouncetime=300)
    except:
        pass
    try:
        CTRL_SW.VOLUME_UP
        GPIO.setup(CTRL_SW.VOLUME_UP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.VOLUME_UP, GPIO.FALLING, callback=p_volumectl, bouncetime=300)
    except:
        pass
    try:
        CTRL_SW.VOLUME_DOWN
        GPIO.setup(CTRL_SW.VOLUME_DOWN,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.VOLUME_DOWN, GPIO.FALLING, callback=p_volumectl, bouncetime=300)
    except:
        pass


    # 音量初期値
    #vol_cmd = 'amixer %s sset PCM %d%%,%d%% unmute > /dev/null 2>&1' % (radio_volume_device, vol_val, vol_val)
    vol_target = volume_profile[vol_val]
    vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (radio_volume_device, radio_volume_ctl, vol_target, vol_target)
    os.system(vol_cmd)
    disp_update()

    try:
        while(True):
            disp_datetime()
            time.sleep(1)
            # 選局操作を行った後実行していない場合のタイムアウト判定
            if p_nexec_count != 0:
                p_nexec_count -= 1
                if p_nexec_count == 0:
                    # タイムアウトしたら選択局を前に戻す
                    p_selected = p_last_selected
                    disp_update()

    except KeyboardInterrupt:
        pass

# Radiko再生
def play_radiko(station, r_user="", r_pass=""):

    # Radikoの再生情報を取得
    ret = radiko.get_radiko_info(station,r_user,r_pass)
    if ret != False:
        (authtoken, streamurl) = ret
        radiko_cmd = "ffplay -nodisp -loglevel quiet -headers \"X-RADIKO-AUTHTOKEN: {0}\" -i {1} >/dev/null 2>&1 &".format(authtoken, streamurl)
        #print(radiko_cmd)
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

#らじる再生
def play_radiru(station):
    radiru_cmd = 'ffplay -nodisp -loglevel quiet -i %s > /dev/null 2>&1 &' % station
    #print(radiru_cmd)
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
    os.system(radiru_cmd)
    return()


#
#####
#
if __name__ == "__main__":
    main()
