コミュニティFMでサイマル(インターネット配信)対応している局はその再生URLがわかれば
対応できます。基本的にらじると同じHLSなのでm3u8のURLを調べてください。

station_listには次のように書きます。

https://musicbird-hls.leanstream.co/musicbird/JCB033.stream/playlist.m3u8,江戸川 FM,EDOGAWA FM,,radiru

らじると同様に局の識別子部分にURLを、再生方法は 'radiru' を指定するだけです。
station_listの記述方法は次の通りです

局識別子,日本語放送局名,英字のみの放送局名,ロゴファイル名,再生方式

ロゴファイルを使用する場合には105x33のPNGファイルを使います。用意するのが面倒な場合には無しでもかまいません。何か入れておきたい場合にはSYS_NET.pngあたりを使ってください。
