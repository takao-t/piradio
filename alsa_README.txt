Raspbinanのバージョンによってオーディオデバイスの名前が変わっているという
問題があるので確認方法をまとめておきます。

aplay -L でオーディオデバイスを確認します。

# aplay -L
null
    Discard all samples (playback) or generate zero samples (capture)
default:CARD=Headphones
    bcm2835 Headphones, bcm2835 Headphones
    Default Audio Device
sysdefault:CARD=Headphones
    bcm2835 Headphones, bcm2835 Headphones
    Default Audio Device
dmix:CARD=Headphones,DEV=0
    bcm2835 Headphones, bcm2835 Headphones
    Direct sample mixing device
dsnoop:CARD=Headphones,DEV=0
    bcm2835 Headphones, bcm2835 Headphones
    Direct sample snooping device
hw:CARD=Headphones,DEV=0
    bcm2835 Headphones, bcm2835 Headphones
    Direct hardware device without any conversions
plughw:CARD=Headphones,DEV=0
    bcm2835 Headphones, bcm2835 Headphones
    Hardware device with all software conversions

この例の場合、Raspberry Pi上の3.5mmジャックのみの環境です。オーディオ出力
用のデバイスとしては Plughw:0 を使います。このデバイスは'0'番目のデバイス
なので、0番目に対する音量コントロールは以下のようにamixerで確認します。

# amixer -c0
Simple mixer control 'Headphone',0
  Capabilities: pvolume pvolume-joined pswitch pswitch-joined
  Playback channels: Mono
  Limits: Playback -10239 - 400
  Mono: Playback 400 [100%] [4.00dB] [on]

結果をみるとわかるように音量コントロールは 'Headphone' です。
USBスピーカやSPI-DAC等を使用しており、例えばPlughw:1を確認する場合には'1'
番目のデバイスなので以下のようにします。

# amixer -c1
Simple mixer control 'PCM',0
  Capabilities: pvolume pvolume-joined pswitch pswitch-joined
  Playback channels: Mono
  Limits: Playback -10239 - 400
  Mono: Playback -9024 [11%] [-90.24dB] [on]

この場合の音量コーントロールは 'PCM' です。

piradioでは音量調整にamixerを使用していますので、これらの方法でオーディオ
の出力先、音量コントロールを設定して使用してください。
