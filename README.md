Raspberry Piをラジオにする(Radiko,らじるらじる,SDR 対応)

![sample](https://user-images.githubusercontent.com/49352933/82976092-272b5800-a019-11ea-9ec7-32c22b80a651.jpg)
![pirate](https://user-images.githubusercontent.com/49352933/83227689-bf634180-a1bf-11ea-97cb-83e33b1f1227.jpg)
![pirate_radio_s](https://user-images.githubusercontent.com/49352933/83390979-c1323c80-a42d-11ea-80bc-6600990643d6.jpg)

要るもの:

どこのご家庭にでもある以下のもを使います
1. Raspberri Pi 3とか4とかZero Wとか
2. GPIOに繋ぐスイッチ5個(PUSH ON)
   プルアップ抵抗5個(*)
   基本は5個ですが最低2個で操作することができます。
3. フレームバッファ(/dev/fbX)として使える液晶(このスクリプトでは320x240を想定)
   AdafruitのPiTFT mini(2.8")を使っていますが、タッチパネル対応がじゃまくさいの
   でタッチには対応していません。スイッチ操作だけです。
   そのへんで売ってる安いSPIのTFTでも/dev/fbXとして動作させられれば使えます
4. 日本語表示用の適当なTTFフォント
5. ffmpegを別途インストールしてください。ffplayを使用します。

*:GPIOにスイッチを繋ぐ場合プルアップし、スイッチはピンとGND間に繋ぎます。


ふつう(piradio.py)版

画面にはpygameを使用していますので、pygameで使えるフレームバッファが必要です。
今のところ Python 2.7 用です

Pirate Audio(piradio_pirate.py)版

画面はPILで書いてます。Pirate Audioはフレームバッファとしては動作させませんが
SPI液晶のPythonライブラリが必要になります。Pirate_README.txtを見てください。


Radikoの再生スクリプトはあちこちにありますが、出所が明確ではないものが多いので新
規に書いて、radiko.pyで実装してあります。Radikoプレミアムにも対応しています。エリ
アフリーを使いたい場合にはプレミアムに登録しメールアドレスとパスワードを設定すれ
ば使えます。 プレミアム使用時に頻繁なログインを避けるため cookieの情報をカレント
ディレクトリに持ちますのでスクリプトが書き込めるディレクトリで起動してください。
他の場所にcookieを保存したい場合にはスクリプトを修正してください。

フレームバッファがない場合でもAPI操作のラジオになります。-noguiを付けて起動する
とAPIだけで動きます。が、初期起動時の音量が小さすぎるので vol_val を調整して起動
してください。

詳細な説明、使い方はWikiを参照してください。

筐体データはここにあります
https://www.thingiverse.com/thing:4417542

アップデート情報及び詳細な使い方等はWikiにあります
https://github.com/takao-t/piradio/wiki
