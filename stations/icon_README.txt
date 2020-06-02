アイコンサイズ 105x33
プロファイルに余計なものが入っているとエラーが出るのでImageMagickで
convert ファイル名 -strip ファイル名を実行して余計なものを取る
さらにカラープロファイルを
convert ファイル名 -define png:color-type=6 ファイル名
で、変換すること

