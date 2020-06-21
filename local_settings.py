#-*- coding: utf-8 -*-

# システム設定
# 
# オーディオ関連の設定は alsa_README.txt も参照のこと
#  オーディオドライバ
radio_audio_driver = 'alsa'
#  出力デバイス
radio_audio_device = 'plughw:1'
# 音量調整デバイス(amixerの引数: -c0 -c1など)
radio_volume_device = '-c1'
# 音量調整コントローラ名
radio_volume_ctl = 'PCM'
# APIのポート(APIを使用しない場合はコメントアウト)
piradio_api_port = 8899

#日本語フォント
jp_font = "mplus-1p-medium.ttf"

# Radikoプレミアム時にセットする
radiko_user = ''
radiko_pass = ''

# 制御用スイッチ:GPIO番号(BCM)
# 注: 使用しないスイッチはコメントアウトして変数をセットしない
#     例えばTUNE_DOWNを指定しなければ合計4ボタンで実装できる
#     音量調整しない場合なら最低2ボタンでも可能
#     ただし再生停止ボタンは必須
# スイッチを接続したGPIO番号に書き換える
class CTRL_SW:
#    STARTSTOP = 18
#    TUNE_UP = 27
#    TUNE_DOWN = 22
#    VOLUME_UP = 21
#    VOLUME_DOWN = 23
    STARTSTOP = 16
    TUNE_UP = 19
    TUNE_DOWN = 20
    VOLUME_UP = 21
    VOLUME_DOWN = 26

# 音量(初期値)
vol_val = 8

# EQでバスブーストする場合のサンプル
#FFPLAY_OPTIONS = '-vn -af "firequalizer=gain_entry=\'entry(0,+8);entry(250,+6)\'" -infbuf -nodisp -loglevel quiet'
