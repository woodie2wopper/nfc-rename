#!/bin/bash
# ImageMagickの magick コマンドを使って、元画像の角をマスク処理で丸める方法です。

# 引数チェック
if [ $# -eq 0 ]; then
  echo "使い方: $0 <入力ファイル名>"
  exit 1
fi

# 入力ファイル名（引数から取得）
INPUT="$1"
# ファイル名と拡張子を取得
FILENAME=$(basename -- "$INPUT")
EXTENSION="${FILENAME##*.}"
BASENAME="${FILENAME%.*}"
# 入力ファイルのディレクトリを取得
DIRNAME=$(dirname -- "$INPUT")

# 出力ファイル名（ディレクトリパスを含む）
OUTPUT="${DIRNAME}/${BASENAME}_rounded.png"
# 画像サイズ（例: 1024x1024）
SIZE=1024
# 角の丸みの半径（サイズの1/4が目安）
RADIUS=256

# 中間ファイル用ディレクトリ作成
mkdir -p ./tmp

# 正方形にリサイズ（必要な場合）
magick "$INPUT" -resize ${SIZE}x${SIZE}^ -gravity center -extent ${SIZE}x${SIZE} ./tmp/square.png

# 角丸マスク作成
magick -size ${SIZE}x${SIZE} xc:none -draw "roundrectangle 0,0,$((SIZE-1)),$((SIZE-1)),$RADIUS,$RADIUS" ./tmp/mask.png

# マスクを適用して角を落とす (CopyOpacity を使用, -alpha off なし)
magick ./tmp/square.png ./tmp/mask.png -compose CopyOpacity -composite "$OUTPUT"

# 中間ファイルを削除（必要なら）
# \rm -f ./tmp/square.png ./tmp/mask.png