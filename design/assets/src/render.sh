#!/bin/zsh
# Renders every card in cards.html to design/assets/ as PNG, with headless Chrome.
# Usage: design/assets/src/render.sh            (all cards)
#        design/assets/src/render.sh lower-third "Name" "Role"

HERE=${0:A:h}
OUT=${HERE:h}
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
shot() { # name width height query
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files \
    --default-background-color=00000000 --virtual-time-budget=3000 \
    --window-size=$2,$3 --screenshot="$OUT/$1.png" "file://$HERE/cards.html?c=$4" >/dev/null 2>&1 || true
  echo "$OUT/$1.png"
}
if [[ $1 == lower-third ]]; then
  shot "lower-third-${2:l:gs/ /-/}" 1920 1080 "lower-third&name=${2// /%20}&role=${3// /%20}"
  exit
fi
for c in card-01-picture-off card-02-title card-03-who card-04-how card-05-library card-06-end lower-third caption; do
  shot $c 1920 1080 $c
done
shot thumbnail-3x2 1500 1000 thumbnail-3x2
shot thumbnail-16x9 1280 720 thumbnail-16x9
