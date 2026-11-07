#!/usr/bin/env bash
# Convert semua texture SVG -> PNG (pakai rsvg-convert / imagemagick / cairosvg)
set -e
cd "$(dirname "$0")/.."
mkdir -p assets

conv() {
  local svg="$1" png="$2" w="$3" h="$4"
  if command -v rsvg-convert >/dev/null 2>&1; then
    rsvg-convert -w "$w" -h "$h" "$svg" -o "$png"
  elif command -v magick >/dev/null 2>&1; then
    magick -background none "$svg" -resize "${w}x${h}!" "$png"
  elif command -v convert >/dev/null 2>&1; then
    convert -background none "$svg" -resize "${w}x${h}!" "$png"
  else
    python -c "import cairosvg,sys; cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[2], output_width=int(sys.argv[3]), output_height=int(sys.argv[4]))" "$svg" "$png" "$w" "$h"
  fi
  echo "  OK -> $png"
}

conv assets_svg/bird.svg        assets/bird.png        128 128
conv assets_svg/pipe_bottom.svg assets/pipe_bottom.png 160 640
conv assets_svg/pipe_top.svg    assets/pipe_top.png    160 640
conv assets_svg/bg.svg          assets/bg.png          720 1280
conv assets_svg/ground.svg      assets/ground.png      720 160
echo "Semua texture PNG siap!"
