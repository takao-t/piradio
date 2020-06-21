#-*- coding: utf-8 -*-

# システム設定
#
#  オーディオドライバ
radio_audio_driver = 'alsa'
# 出力デバイス
# Pirate AudioのI2S DACを使用するので注意
radio_audio_device = 'softvol'
# 音量調整デバイス(amixerの引数: -c0 -c1など)
radio_volume_device = '-c0'
# コントロールデバイス
radio_volume_ctl = 'SoftMaster'
#
# APIのポート(APIを使用しない場合はコメントアウト)
#radio_api_port = 8899

# Radikoプレミアムでエリアフリーを使う場合には設定する
radiko_user = ''
radiko_pass = ''

#日本語フォント
jp_font = "mplus-1p-bold.ttf"

# 制御用スイッチ:GPIO番号(BCM)
# Pirate Audio上のプッシュスイッチ(TUNE_DOWNは使わない)
#
class CTRL_SW:
    STARTSTOP = 16  # X
    TUNE_UP = 20    # Y 20で動作しない場合は24に変更する
    VOLUME_UP = 5   # A
    VOLUME_DOWN = 6 # B
# Line-out モデルの場合は音量調整要らないので以下の設定
# で音量調整なしがお勧め
#    STARTSTOP = 20  # Y 20で動作しない場合は24に変更する
#    TUNE_DOWN = 5   # A
#    TUNE_UP = 6     # B

# 音量(初期値:0-31)
# Line-out モデルの場合は音量調整しないので最大(31)にする
# またはレベル調整した固定値にする
# 音量の調整が不要ならsoftvolを使わず直接hifiberryを指定
# してかまわない
vol_val = 10

# EQでバスブーストする場合のサンプル
#FFPLAY_OPTIONS = '-vn -af "firequalizer=gain_entry=\'entry(0,+8);entry(250,+6)\'" -infbuf -nodisp -loglevel quiet'
