#-*- coding: utf-8 -*-

# Raspberry Pi+Pirate Audioをradikoラジオにする
# Python 2.7 対応 (3も動く)
#
# 要るもの:
# Pirate Audioのどれか
# Raspberri Pi Zero Wとか3とか
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

# Pirate AudioのSPI液晶
from colorsys import hsv_to_rgb
from PIL import Image, ImageDraw, ImageFont
from ST7789 import ST7789

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


import pirate_local_settings as local_settings


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
# 音量(初期値)
try:
    vol_val = local_settings.vol_val
except:
    vol_val = 10

# 局設定リストのファイル
station_file = 'stations/station_list'
# ロゴファイルのパス
station_logo_path = 'stations/'
# ロゴのクロップサイズ
logo_crop_size = (5,0,110,33)
# ロゴ縦位置
logo_offset_y = 2

# ffplayのオプション
FFPLAY_OPTIONS = '-vn -infbuf -nodisp -loglevel quiet'

# 画面背景色
sc_bg_color = (0,200,200)
# 選択項目表示色
#b_bright = (150,50,20)
b_bright = (220,220,220)
# 暗表示色
#b_dark = (96,96,96)
b_dark = (160,160,160)
# ビジー色
b_busy = (255,0,0)
# 局名テキスト表示色
#st_text_color = (180, 180, 180)
st_text_color = (0, 0, 0)
# 音量ポップアップ色
vol_popup_color = (0,255,255)

# 局名表示横幅
station_disp_x = 240
# 局名表示縦幅
station_disp_y = 37
# 局名表示文字位置オフセット
text_offset_x = 100
text_offset_y = 4
#text_offset_y = 0

# SPI LCD
SPI_SPEED_MHZ = 80

st7789 = ST7789(
    rotation=90,  # Needed to display the right way up on Pirate Audio
    port=0,       # SPI port
    cs=1,         # SPI port Chip-select channel
    dc=9,         # BCM pin used for data/command
    backlight=13,
    spi_speed_hz=SPI_SPEED_MHZ * 1000 * 1000
)
# スクリーンクリア
sc_image = Image.new("RGB", (240, 240), (sc_bg_color))
sc_draw = ImageDraw.Draw(sc_image)
sc_draw.rectangle((0,0,240,120),fill=(0,0,0),outline=(0,0,0) )
st7789.display(sc_image)

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
# 右下アイコン色
b_icon_color = b_dark

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

# 局名リスト
station_lists = []
#局数
num_stations = 0


try:
    use_gui
    # フォント
    # フォントはスクリプトが読めるところに置いたTTFフォント
    # 画面上の局名表示用
    font1 = ImageFont.truetype(jp_font_to_use, 22)
    # 音量表示用
    font2 = ImageFont.truetype(jp_font_to_use, 40)
    # ポップアップ表示用
    font3 = ImageFont.truetype(jp_font_to_use, 40)

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

        cmd = self.data.split(b' ',2)[0]
        cmd = cmd.decode('utf-8')
        try:
            target = self.data.split(b' ',2)[1]
            target = target.decode('utf-8')
        except:
            target = ''
        #print(cmd)
        #print(target)

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
        if cmd == 'NEWLIST':
            print('NEWLIST')
            #print('NEWLIST command for %s' % target)
            api_p_stop()
            api_p_listupdate(target)
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
    # 再生開始のWAITの表示
    try:
        use_gui
        popup_text('WAIT',(255,174,0))
    except:
        pass
    # 再生を強制停止
    os.system('killall ffplay')
    time.sleep(0.5)
    station_num = p_selected
    (station_id, dummy1, dummy2, dummy3, p_method) = station_lists[station_num]
    # 再生方法がRadiko
    if p_method == 'radiko':
        play_radiko(station_id,radiko_user,radiko_pass)
    # 再生方法がらじる
    if p_method == 'radiru':
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
    # 再生ストップの表示
    try:
        use_gui
        popup_text('STOP',(255,0,0))
    except:
        pass
    # 再生を停止
    os.system('killall ffplay')
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

    try:
        use_gui
        disp_update()
    except:
        pass


# シグナルハンドラ(終了処理)
def signal_handler(signal,stack):
    print('Got signal: Quiting...')
    try:
        api_server.shutdown()
    except:
        pass
    os.system('killall ffplay')
    time.sleep(1)
    try:
        use_gui
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
    global b_icon_color

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
        b_icon_color = b_dark
        # 選局操作を行った後なら再度再生実行
        if p_selected != p_last_selected:
             do_pb = 1
    except:
        # 現在再生されていないので再生実行
        do_pb = 1

    if do_pb == 1:

        b_icon_color = b_busy

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

    if p_method == 'radiko' or p_method == 'radiru':
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


# 再生/停止
def p_startstop(pinnum):
    #print(pinnum)

    global p_selected
    global p_last_selected
    global p_nexec_count
    global p_nexec_timeout
    global b_icon_color

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
            vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
            #volume_text = "%d" % vol_val
            #popup_text(volume_text,(vol_popup_color))
            #time.sleep(0.2)
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
            vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
            #volume_text = "%d" % vol_val
            #popup_text(volume_text,(vol_popup_color))
            #time.sleep(0.2)
            os.system(vol_cmd)
    except:
        pass

    disp_update()
    #print(vol_val)

# 画面表示更新
def disp_update():

    global p_selected
    global sc_draw
    global sc_image

    try:
        use_gui
        #print(p_selected)

        sc_draw.rectangle((0,0,239,239),fill=(sc_bg_color),outline=(0,0,0) )

        dsp_page = int(p_selected / station_per_page) * station_per_page
        dsp_pos = p_selected - dsp_page

        b_count = 0
        text_org_x = text_offset_x
        text_org_y = text_offset_y

        disp_y_next = 0

        ta_len = len(station_lists)

        b_pos = 0
        for b_pos in range(station_per_page):
            if dsp_pos == b_pos:
                b_brightness = b_bright
            else:
                b_brightness = b_dark
            sc_draw.rectangle((0,disp_y_next,station_disp_x,(disp_y_next+station_disp_y)),fill=(b_brightness),outline=(0,0,0) )
            #ページ内の表示局数が下までない場合にはテキストを書かない(書けない)
            if (b_pos+dsp_page) < ta_len:
                (dummy1,station_name,dummy2,logo_file,dummy4) = station_lists[b_pos+dsp_page]
                l_full_path = "%s%s" % (station_logo_path, logo_file)
                sc_draw.text((text_org_x,disp_y_next+text_org_y),station_name,st_text_color,font=font1)
                if logo_file != "":
                    try:
                        st_logo = Image.open(l_full_path)
                        st_logo = st_logo.crop(logo_crop_size)
                        sc_image.paste(st_logo,(0,disp_y_next+logo_offset_y),st_logo)
                    except:
                        pass
            disp_y_next += (station_disp_y + 2)
            b_count += 1

        # ボリューム値バー
        tmp_corner = vol_val * 6
        sc_draw.rectangle((0,232,tmp_corner,239),fill=(0,255,0),outline=(b_dark) )
        #
        sc_draw.rectangle((200,232,239,239),fill=(b_icon_color),outline=(b_dark) )

        st7789.display(sc_image)
        time.sleep(0.1)
    except:
        pass

# 画面上ポップアップテキスト
def popup_text(text,color):
    global sc_image
    global sc_draw
    try:
        use_gui
        sc_draw.text((70,70),text,color,font=font3)
        st7789.display(sc_image)
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
    vol_target = volume_profile[vol_val]
    vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
    os.system(vol_cmd)
    disp_update()

# 局名リスト読み込み処理
def read_stations(signal="",frame="",filename=""):

    global station_lists
    global num_stations
    global p_selected
    global p_last_selected

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


# メイン処理
def main():

    global p_nexec_count
    global p_selected
    global p_last_selected
    global g_ps_pressed

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
    try:
        CTRL_SW.STARTSTOP
        GPIO.setup(CTRL_SW.STARTSTOP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(CTRL_SW.STARTSTOP, GPIO.FALLING, callback=p_startstop, bouncetime=300)
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

    #局名リスト初期化
    read_stations("","",station_file)

    #オーディオデバイスをセット
    audio_dev_set(audio_list)

    # 音量初期値
    #vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (audio_vol_device, audio_vol_ctl, vol_val, vol_val)
    vol_target = volume_profile[vol_val]
    vol_cmd = 'amixer %s sset %s %d%%,%d%% unmute > /dev/null 2>&1' % (AUDIODEV.VOLDEV, AUDIODEV.VCONT, vol_target, vol_target)
    os.system(vol_cmd)
    disp_update()

    try:
        while(True):
            # 再生/停止指定があった場合は実行
            if g_ps_pressed == 1:
                pbs_control_sub()
                g_ps_pressed = 0
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
        radiko_cmd = "ffplay {2} -headers \"X-RADIKO-AUTHTOKEN: {0}\" -i {1} >/dev/null 2>&1 &".format(authtoken, streamurl, FFPLAY_OPTIONS)
        #print(radiko_cmd)
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
        os.system(radiko_cmd)
        return()

    return()

#らじる再生
def play_radiru(station):
    radiru_cmd = 'ffplay -vn -infbuf -nodisp -loglevel quiet -i %s > /dev/null 2>&1 &' % station
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


#
#####
#
if __name__ == "__main__":
    main()
