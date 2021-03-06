#-*- coding: utf-8 -*-

# Raspberry Piをradikoラジオにする
# Python 2.7 対応 (3は一部書き換えて)
#
# 要るもの:
# Raspberri Pi 3とか4とかZero Wとか
# GPIOに繋ぐスイッチ5(2<)個
# フレームバッファ(/dev/fbX)として使える液晶
# このスクリプトでは320x240を想定
# 画面にはpygameを使用
# 要するにpygameで表示できればOK

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
# らじる処理用
import radiru
# サイマルラジオ処理用
import simulradio


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

import local_settings

try:
    radio_audio_driver = local_settings.radio_audio_driver
except:
    radio_audio_driver = 'alsa'
try:
    radio_audio_device = local_settings.radio_audio_device
except:
    radio_audio_device = 'plughw:0'
try:
    radio_volume_device = local_settings.radio_volume_device
except:
    radio_volume_device = 'Headdphone'
try:
    radio_volume_ctl = local_settings.radio_volume_ctl
except:
    radio_volume_ctl = '-c0'
try:
    piradio_api_port = local_settings.radio_api_port
except:
    pass
try:
    jp_font_to_use = local_settings.jp_font
except:
    jp_font_to_use = "mplus-1p-medium.ttf"

#オーディオデバイスをリスト化
audio_list = radio_audio_driver + ';' + radio_audio_device + ';' + radio_volume_device + ';' + radio_volume_ctl

# Radikoプレミアムでエリアフリーを使う場合には設定する
try:
    radiko_user = local_settings.radiko_user
    radiko_pass = local_settings.radiko_pass
except:
    pass

# 制御用スイッチ
try:
    CTRL_SW = local_settings.CTRL_SW
except:
    pass
# バックライト制御ピン
try:
    BACKLIGHT = local_settings.BACKLIGHT
except:
    pass
# 音量(初期値)
try:
    vol_val = local_settings.vol_val
except:
    vol_val = 10

# 局設定リストのファイル
try:
    station_file = local_settings.station_file
except:
    station_file = 'stations/station_list'
# ロゴファイルのパス
try:
    station_logo_path = local_settings.station_logo_path
except:
    station_logo_path = 'stations/'

# 320x240のディスプレイを使用
# pygameで使用するフレームバッファだけあればOK
os.putenv('SDL_FBDEV', '/dev/fb1')

# ffplayのオプション
try:
    FFPLAY_OPTIONS
except:
    FFPLAY_OPTIONS = '-vn -infbuf -nodisp -loglevel quiet'

# バックライト消灯までの時間
try:
    BL_TIMEOUT = local_settings.BL_TIMEOUT
except:
    BL_TIMEOUT = 30

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
# 再生が押されたかどうか
g_ps_pressed = 0
# 再生方法受け渡し
g_p_method = ''

# 音量調整用プロファイル(32段階)
volume_profile = [ 0, 6, 9,12,15,18,21,24,27,30,33,36,39,42,45,48, \
                  51,54,57,60,63,66,69,72,75,78,81,84,87,90,93,96 ]

## オーディオデバイス(内部処理用)
class AUDIODEV:
    try:
        DRIVER = radio_audio_driver
    except:
        pass
    try:
        OUTDEV = radio_audio_device
    except:
        pass
    try:
        VOLDEV = radio_volume_device
    except:
        pass
    try:
        VCONT  = radio_volume_ctl
    except:
        pass

# GPIOの問題避け
prev_pushed_time = 0

# キー操作フラグ
key_pressed = 0
key_timeout = 0

# 再生停止コマンド
stop_play_cmd = 'killall ffplay'

# 局名リスト
num_stations = 0
station_lists = []
texts = []

try:
    use_gui
    # pygame初期化
    pygame.init()
    screen = pygame.display.set_mode((320, 240))
    pygame.mouse.set_visible(False)
    pygame.mixer.quit()


    #背景色
    screen.fill(sc_bg_color)
    pygame.display.update()

    # フォント
    # フォントはスクリプトが読めるところに置いたTTFフォント
    # 画面上の局名表示用
    #font1 = pygame.font.Font("ipaexg.ttf", 24)
    #font1 = pygame.font.Font("azukiLB.ttf", 24)
    #font1 = pygame.font.Font("TanukiMagic.ttf", 24)
    font1 = pygame.font.Font(jp_font_to_use, 20)
    # 音量表示用
    font2 = pygame.font.SysFont(None, 128)
    # "WAIT"表示用
    font3 = pygame.font.SysFont(None, 64)
    # ミニフォント(画面下部表示用)
    font4 = pygame.font.SysFont(None, 22)

    #表示局名生成
    #texts = []
    #for tmp_pos in range(num_stations):
    #    (dummy1, station_text, dummy2, dummy3, dummy4) = station_lists[tmp_pos]
    #    if station_text == "":
    #        station_text = "  "
    #    texts.append( font1.render(station_text, True, st_text_color) )

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
        global key_pressed

        key_pressed = 1

        self.data = self.request.recv(256).strip()

        cmd = self.data.split(b' ',2)[0]
        cmd = cmd.decode('utf-8')
        try:
            target = self.data.split(b' ',2)[1]
            target = target.decode('utf-8')
        except:
            target = ''
        print(cmd)
        print(target)

        if cmd == 'START':
            #print('START command for %s' % target)
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
        if cmd == 'NEWLIST':
            print('NEWLIST')
            #print('NEWLIST command for %s' % target)
            api_p_stop()
            api_p_listupdate(target)
            self.request.sendall("OK\n".encode('utf-8'))
            return(True)
        if cmd == 'VOLUP':
            s_volume_up()
            self.request.sendall("OK\n".encode('utf-8'))
            return(True)
        if cmd == 'VOLDN':
            s_volume_dn()
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
    try:
        use_gui
        popup_text('WAIT',(255,174,0))
    except:
        pass
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
    # 再生方法がASX再生
    if p_method == 'play_asx':
        stop_play_cmd = 'killall mplayer'
        play_asx(station_id)
    # 再生方法がサイマルラジオ
    if p_method == 'simulradio':
        stop_play_cmd = 'killall mplayer'
        play_simulradio(station_id)
    # 再生方法がストリーム
    if p_method == 'stream':
        stop_play_cmd = 'killall ffplay'
        play_stream(station_id)
    # 再生方法がSDR
    if p_method == 'sdr_radio':
        stop_play_cmd = 'killall ffplay'
        play_sdr_radio(station_id)
    #
    p_last_selected = p_selected
    p_nexec_count = 0
    # WAIT表示のままちょいまち
    time.sleep(1)
    disp_update()
    print("API-PLAY : %s" % station_id)

# APIからの停止処理
def api_p_stop():
    global stop_play_cmd
    # 再生ストップの表示
    try:
        use_gui
        popup_text('STOP',(255,0,0))
    except:
        pass
    # 再生を停止
    os.system(stop_play_cmd)
    time.sleep(0.5)
    disp_update()
    print("API-STOP")

# APIからの局リスト更新
def api_p_listupdate(filename):
    global p_selected
    global p_last_selected

    p_selected = 0
    p_last_selected =0

    read_stations("","",filename)

    disp_update()


# シグナルハンドラ(終了処理)
def signal_handler(signal,stack):
    global stop_play_cmd
    print('Got signal: Quiting...')
    try:
        api_server.shutdown()
    except:
        pass
    os.system(stop_play_cmd)
    time.sleep(1)
    try:
        use_gui
        pygame.quit()
    except:
        pass
    GPIO.cleanup()
    sys.exit()

# 再生/停止サブ処理
def pbs_control_sub():

    global p_selected
    global p_last_selected
    global p_nexec_count
    global p_nexec_timeout
    global stop_play_cmd
    global g_p_method

    p_method = g_p_method

    try:
        stop_arg = stop_play_cmd.split(' ')
        res = subprocess.check_output(["pgrep",stop_arg[1]])
        # 再生ストップスタートのWAIT表示
        popup_text('STOP',(255,0,0))
        # 再生を停止
        os.system(stop_play_cmd)
        time.sleep(1)
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
            # WAIT表示のままちょいまち
            time.sleep(1)
        # 再生方法がらじる
        if p_method == 'radiru':
            stop_play_cmd = 'killall ffplay'
            play_radiru(station_id)
            # WAIT表示のままちょいまち
            time.sleep(1)
        # 再生方法がASX再生
        if p_method == 'play_asx':
            stop_play_cmd = 'killall mplayer'
            play_asx(station_id)
            # WAIT表示のままちょいまち
            time.sleep(1)
        # 再生方法がサイマルラジオ
        if p_method == 'simulradio':
            stop_play_cmd = 'killall mplayer'
            play_simulradio(station_id)
            # WAIT表示のままちょいまち
            time.sleep(1)
        # 再生方法がストリーム
        if p_method == 'stream':
            stop_play_cmd = 'killall ffplay'
            play_stream(station_id)
            # WAIT表示のままちょいまち
            time.sleep(1)
        # 再生方法がSDR
        if p_method == 'sdr_radio':
            stop_play_cmd = 'killall ffplay'
            play_sdr_radio(station_id)
            # WAIT表示のままちょいまち
            time.sleep(1)
        p_last_selected = p_selected
    disp_update()


# 再生/停止(実処理)
def p_pbs_control():

    global p_selected
    global p_last_selected
    global p_nexec_count
    global p_nexec_timeout
    global stop_play_cmd
    global g_p_method
    global g_ps_pressed

    station_num = p_selected
    (station_id, dummy1, dummy2, dummy3, p_method) = station_lists[station_num]

    g_p_method = p_method

    if p_method == 'radiko' or p_method == 'radiru' \
                    or p_method == 'sdr_radio' or p_method == 'stream' \
                    or p_method == 'play_asx' or p_method == 'simulradio':
        g_ps_pressed = 1
        #pbs_control_sub()
    else:
        # 外部コマンド
        if p_method == 'COMMAND':
            try:
                station_id
                if station_id != "":
                    os.system(station_id)
            except:
                pass
            p_selected = p_last_selected
        # メニューリロード処理
        if p_method == 'MENU':
            try:
                stop_play_cmd
                os.system(stop_play_cmd)
            except:
                pass
            try:
                station_id
                p_last_selected = 0
                p_selected  = 0
                read_stations("","",station_id)
                time.sleep(1)
                disp_update()
            except:
                pass
        # オーディオデバイス切換
        if p_method == 'AUDIOSET':
            try:
                stop_play_cmd
                os.system(stop_play_cmd)
            except:
                pass
            try:
                station_id
                audio_dev_set(station_id)
                popup_text('OK',(255,0,0))
                time.sleep(1)
            except:
                pass



# 再生/停止ボタン処理
def p_startstop(pinnum):
    #print(pinnum)

    global p_selected
    global p_last_selected
    global p_nexec_count
    global p_nexec_timeout
    global stop_play_cmd
    global key_pressed


    # GPIO割込みが2重検出される問題避け
    # 他のスイッチではあまり問題ではないがSTART/STOPだけは大問題なのでworkaround
    global prev_pushed_time
    guard_time = 0.2

    # GPIO割込みの2重検出避け
    pushed_time = time.time()
    if (pushed_time - prev_pushed_time) < guard_time:
        return()
    prev_pushed_time = time.time()

    p_pbs_control()

    #元画面再表示
    disp_update()
    key_pressed = 1


# 選局
def p_tunectl(pinnum):
    #print(pinnum)

    global p_selected
    global p_nexec_count
    global key_pressed

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
    key_pressed = 1

# 音量up
def s_volume_up():

    global vol_val

    vol_val += 1
    if vol_val >= 31:
        vol_val = 31
    vol_target = volume_profile[vol_val]
    vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
    os.system(vol_cmd)
    disp_update()

# 音量dn
def s_volume_dn():

    global vol_val

    vol_val -= 1
    if vol_val <= 0:
        vol_val = 0
    vol_target = volume_profile[vol_val]
    vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
    os.system(vol_cmd)
    disp_update()


# 音量
def p_volumectl(pinnum):

    global key_pressed
    #print(pinnum)

    try:
        CTRL_SW.VOLUME_UP
        if pinnum == CTRL_SW.VOLUME_UP:
            s_volume_up()
    except:
        pass
    try:
        CTRL_SW.VOLUME_DOWN
        if pinnum == CTRL_SW.VOLUME_DOWN:
            s_volume_dn()
    except:
        pass

    key_pressed = 1


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

# オーディオデバイス変更処理
def audio_dev_set(list):

    global AUDIODEV
    global vol_val

    audio_setting = list.split(';')
    #print(audio_setting)

    AUDIODEV.DRIVER = audio_setting[0]
    AUDIODEV.OUTDEV = audio_setting[1]
    AUDIODEV.VOLDEV = audio_setting[2]
    AUDIODEV.VCONT  = audio_setting[3]
    try:
        #print(int(audio_setting[4]))
        audio_setting[4]
        vol_val = int(audio_setting[4])
    except:
        pass

    #print(vol_val)

    #音量設定しなおし
    # 音量初期値
    # 初期値+1してdownで設定しなおす
    vol_val += 1
    s_volume_dn()
    disp_update()


# 局名リスト読み込み処理
def read_stations(signal="",frame="",filename=""):

    global num_stations
    global station_lists
    global texts
    global p_selected
    global p_last_selected

    #print(signal)
    #print(frame)
    #print(filename)


    #
    try:
        filename
        if filename != "":
            load_fn = filename
            #print('exsplicit load')
        else:
            load_fn = station_file
    except:
        load_fn = station_file

    try:
        # For Python2
        with codecs.open(load_fn, 'r', 'utf-8') as f:
        # For Python3
        #with open(load_fn, 'r', encoding='utf-8') as f:
            num_stations = 0
            texts = []
            station_lists = []
            s_line = f.readline()
            while s_line:
                if not s_line.startswith('#'):
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
        #現在選択位置が全局数より大きければ初期化
        if p_selected > num_stations:
            p_selected = 0
            p_last_selected = 0
    except:
        pass

    #表示局名生成
    try:
        use_gui
        texts = []
        for tmp_pos in range(num_stations):
            (dummy1, station_text, dummy2, dummy3, dummy4) = station_lists[tmp_pos]
            if station_text == "":
                station_text = "  "
            texts.append( font1.render(station_text, True, st_text_color) )
    except:
        pass


# メイン処理
def main():

    global p_nexec_count
    global p_selected
    global p_last_selected
    global g_ps_pressed
    global vol_val
    global key_pressed
    global key_timeout

    # シグナル(HUP,INT,QUITで終了)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGQUIT, signal_handler)

    # 局リスト再読み込み
    signal.signal(signal.SIGUSR1, read_stations)


    # GPIOセットアップ
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    # 各ピンを入力,プルアップありにしピンの割り込みハンドラを設定
    # 外部プルアップ制御時
    try:
        CTRL_SW.PULLUP
        GPIO.setup(CTRL_SW.PULLUP,GPIO.OUT)
        GPIO.output(CTRL_SW.PULLUP,GPIO.HIGH)
    except:
        pass
    # 各スイッチのピンセットアップ
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
    # バックライト制御
    try:
        BACKLIGHT
        GPIO.setup(BACKLIGHT,GPIO.OUT)
        GPIO.output(BACKLIGHT,GPIO.HIGH)
    except:
        pass

    #局名リスト初期化
    read_stations("","",station_file)

    #オーディオデバイスをセット
    audio_dev_set(audio_list)

    # 音量初期値
    # 初期値+1してdownで初期設定
    vol_val += 1
    s_volume_dn()
    disp_update()

    try:
        while(True):
            # 再生/停止指定があった場合は実行
            if g_ps_pressed == 1:
                pbs_control_sub()
                g_ps_pressed = 0
            disp_datetime()
            # 選局操作を行った後実行していない場合のタイムアウト判定
            if p_nexec_count != 0:
                p_nexec_count -= 1
                if p_nexec_count == 0:
                    # タイムアウトしたら選択局を前に戻す
                    p_selected = p_last_selected
                    disp_update()
            try:
                BACKLIGHT
                # 操作タイムアウトでバックライト消灯
                key_timeout += 1
                if BL_TIMEOUT != 0:
                    if key_timeout > BL_TIMEOUT:
                        GPIO.output(BACKLIGHT,GPIO.LOW)
                    if key_pressed == 1:
                        key_timeout = 0
                        key_pressed = 0
                        GPIO.output(BACKLIGHT,GPIO.HIGH)
            except:
                pass
            # ループサイクルは1秒
            time.sleep(1)

    except KeyboardInterrupt:
        pass

# Radiko再生
def play_radiko(station, r_user="", r_pass=""):

    # Radikoの再生情報を取得
    ret = radiko.get_radiko_info(station,r_user,r_pass)
    if ret != False:
        (authtoken, streamurl) = ret
        radiko_cmd = "ffplay {2} -headers \"X-RADIKO-AUTHTOKEN: {0}\" -i {1} > /dev/null 2>&1 &".format(authtoken, streamurl, FFPLAY_OPTIONS)
        #print(radiko_cmd)
        try:
            AUDIODEV.DRIVER
            os.putenv('SDL_AUDIODRIVER', AUDIODEV.DRIVER)
        except:
            pass
        try:
            AUDIODEV.OUTDEV
            #print(AUDIODEV.OUTDEV)
            os.putenv('AUDIODEV', AUDIODEV.OUTDEV)
        except:
            pass
        os.system(radiko_cmd)
        return()

    return()

#らじる再生
def play_radiru(station):
    ret = radiru.radiru_url(station)
    if ret != False:
        radiru_cmd = "ffplay {1} -i {0} > /dev/null 2>&1 &".format(ret, FFPLAY_OPTIONS)
        #print(radiru_cmd)
        try:
            AUDIODEV.DRIVER
            os.putenv('SDL_AUDIODRIVER', AUDIODEV.DRIVER)
        except:
            pass
        try:
            AUDIODEV.OUTDEV
            os.putenv('AUDIODEV', AUDIODEV.OUTDEV)
        except:
            pass
        os.system(radiru_cmd)
    return()

#サイマルラジオ対応
def play_simulradio(station):
    if station != '':
        target = simulradio.get_simulradio_url(station)
        #print(target)
        try:
            AUDIODEV.DRIVER
            AUDIODEV.OUTDEV
            tmp_dev = AUDIODEV.OUTDEV.replace(':','=')
            asx_cmd = "mplayer -novideo -ao %s:device=%s %s > /dev/null 2>&1 &" % (AUDIODEV.DRIVER, tmp_dev, target)
        except:
            asx_cmd = "mplayer -novideo %s > /dev/null 2>&1 &" % target

        #print(asx_cmd)
        os.system(asx_cmd)
    return


#ASX対応
def play_asx(station):
    if station != '':
        target = simulradio.asx_to_target(station)
        #print(target)
        try:
            AUDIODEV.DRIVER
            AUDIODEV.OUTDEV
            tmp_dev = AUDIODEV.OUTDEV.replace(':','=')
            asx_cmd = "mplayer -novideo -ao %s:device=%s %s > /dev/null 2>&1 &" % (AUDIODEV.DRIVER, tmp_dev, target)
        except:
            asx_cmd = "mplayer -novideo %s > /dev/null 2>&1 &" % target

        #print(asx_cmd)
        os.system(asx_cmd)
    return

#ストリーム再生(URL指定)
def play_stream(s_url):
    if s_url != '':
        stream_cmd = "ffplay {1} -i {0} > /dev/null 2>&1 &".format(s_url, FFPLAY_OPTIONS)
        #print(stream_cmd)
        try:
            AUDIODEV.DRIVER
            os.putenv('SDL_AUDIODRIVER', AUDIODEV.DRIVER)
        except:
            pass
        try:
            AUDIODEV.OUTDEV
            os.putenv('AUDIODEV', AUDIODEV.OUTDEV)
        except:
            pass
        os.system(stream_cmd)
    return()

# SDR
def play_sdr_radio(station):

    freq = station.split(b';')[0]
    try:
        demod = station.split(b';')[1]
    except:
        demod = 'AM'

    option = ''
    if demod == 'AM':
        demod = 'am'
    elif demod == 'NFM':
        demod = 'fm'
    elif demod == 'WFM':
        demod = 'wbfm'
        option = '-E demp'
    elif demod == 'USB':
        demod = 'usb'
    elif demod == 'LSB':
        demod = 'lsb'
    else:
        demod = 'am'

    sdr_radio_cmd = 'rtl_fm -f %s -M %s %s -s 200000 -r 44100 - ' % (freq, demod, option)
    sdr_play_cmd = 'ffplay -f s16le -ar 44100 -i -'
    try:
        AUDIODEV.OUTDEV
        os.putenv('AUDIODEV', AUDIODEV.OUTDEV)
    except:
        pass
    sdr_cmd = sdr_radio_cmd + ' 2> /dev/null |' + sdr_play_cmd + ' > /dev/null 2>&1 &'
    #print(sdr_cmd)
    time.sleep(1)
    os.system(sdr_cmd)
    return()


#
#####
#
if __name__ == "__main__":
    main()
