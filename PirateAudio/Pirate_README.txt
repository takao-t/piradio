Pirate Audio対応

piradio_pirate.py がPirate Audio対応用です。フレームバッファ版と比較して以下が異なります。

・4ボタン制御です
　Pirate Audio上のボタンだけで制御します
　選局はUPしかありません。DOWN側がないので局リストを長くしすぎると面倒になります
  ただし、コードとしては存在しているのでGPIOからスイッチを引き出せば5ボタン制御
　にも改造できます。
　この際、使用するGPIOについて注意してください。Pirate Audio上のスイッチが5,6,16と
  20または24を、DACが25を、液晶が9と13を使用しています。

・下に表示する音量と時計はありません
　小さすぎて見えないので実装していません


〇セットアップ

radiko.pyが必要なのでpiradio_pirate.pyと同じディレクトリにコピーしておいてください。
このプログラム自体はPythonなので特に問題はないのですが、Pirate AudioのI2S DACが
音量調整を持たないのでひと工夫が必要です。

mopidyをインストールする必要はないので、入れなくてかまいません。というかmopidy
入れてプレイヤーにしてしまうとラジオにならないです。

raspi-configでSPIを有効にしておきます。
I2S DACを使用するため /boot/config.txtに以下を追加します。

dtoverlay=hifiberry-dac
gpio=25=op,dh


DACの音量制御がない(わからない)ので、ALSAのSoftVolumeを使います。
なお、Line-Outモデルは音量調整の必要は大抵は無いのでSoftVolumeを設定する必要はありません。

/usr/share/alsaにあるalsa.confの最後に以下を追記します。

----------
pcm.softvol {
    type            softvol
    slave {
        pcm         "plughw:1"
    }
    control {
        name        "SoftMaster"
        card        0
    }
}

pcm.!default {
    type             plug
    slave.pcm       "softvol";
}
----------
注:alsa.confに記述しても動作しない場合には /etc/asound.conf に上の内容を書いてください。
(Raspbianのアップデートで挙動が変わってます)

ここで注意ですが、pcm "plughw:1"のところがI2S DACを指すようにしてください。
オンボードサウンド、HDMI等がある場合には "plughw:0"や2がI2S DACになる場合が
ありますので、正しくI2S DACを指すようにします。
aplay -L で以下のようなエントリがI2S DACです。

plughw:CARD=sndrpihifiberry,DEV=0
    snd_rpi_hifiberry_dac, HifiBerry DAC HiFi pcm5102a-hifi-0
    Hardware device with all software conversions

上記の設定で、'softvol'->音量調整->'plughw:0' になるのでサウンドデバイス
として'softvol'を指定すると音量調整の効くI2S-DACとなります。
これによりpythonプログラム側の設定は以下のようになります。

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

I2S DACが2番目のデバイスとして認識されている場合にはasound.confでは"plughw:1:を設定し、pythonの-c0を-c1に変更してください。

Line-OutモデルでSoftVolumeを使用していない場合にはオーディオ出力デバイスとしてI2S-DACを直接してしまえばよいです。(例:plughw:1)

PythonのモジュールST7789が必要になりますので、pipでインストールしてください。
PILとかも必要になるのでソースを見て入れてください。(PILはaptで入れる方が簡単)

だいたいこんな感じ(元から入っている場合もあるので足りなければ)
pip install spi pillow gpio

注：このバージョンもフォントがないと固まったようにみえるのでフォントを自分で入れてください
