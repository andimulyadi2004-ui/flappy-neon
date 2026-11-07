#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

REPO="flappy-neon"

echo "==> [1/6] Generate texture PNG dari SVG..."
bash tools/svg2png.sh

echo "==> [2/6] Simpan ke git..."
git init -b main >/dev/null 2>&1 || git init >/dev/null
git config user.name  "flappy-builder"
git config user.email "flappy@builder.local"
git add -A
git commit -m "Flappy Neon v1.0" >/dev/null || true

echo "==> [3/6] Push ke GitHub..."
if ! git remote get-url origin >/dev/null 2>&1; then
  if ! gh repo create "$REPO" --public --source=. --push; then
    REPO="$REPO-$(date +%s)"
    echo "    Nama repo sudah dipakai, pakai: $REPO"
    gh repo create "$REPO" --public --source=. --push
  fi
else
  git push -u origin main
fi

echo "==> [4/6] Tunggu GitHub Actions build APK (build pertama +/- 15-30 menit)..."
termux-wake-lock >/dev/null 2>&1 || true
sleep 25
RUN=""
for i in 1 2 3 4 5 6; do
  RUN=$(gh run list --workflow=build-apk.yml --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)
  if [ -n "$RUN" ] && [ "$RUN" != "null" ]; then break; fi
  echo "    Run belum muncul, cek lagi ($i/6)..."
  sleep 15
done
if [ -z "$RUN" ] || [ "$RUN" == "null" ]; then
  echo "GAGAL: run tidak ditemukan. Cek manual: gh run list"
  exit 1
fi
echo "    Run ID: $RUN"
if ! gh run watch "$RUN"; then
  echo "BUILD GAGAL di server. Lihat errornya dengan:"
  echo "  gh run view $RUN --log-failed | tail -n 80"
  exit 1
fi

echo "==> [5/6] Download APK dari GitHub..."
rm -rf dist
mkdir -p dist
gh run download "$RUN" --name flappy-apk --dir dist

echo "==> [6/6] Pindahkan ke folder Download HP..."
termux-setup-storage >/dev/null 2>&1 || true
sleep 2
cp dist/FlappyNeon.apk ~/storage/shared/Download/FlappyNeon.apk
termux-wake-unlock >/dev/null 2>&1 || true

echo ""
echo "=============================================="
echo " SELESAI! APK ada di folder Download HP:"
echo "   /storage/emulated/0/Download/FlappyNeon.apk"
echo ""
echo " Install langsung dari Termux:"
echo "   termux-open ~/storage/shared/Download/FlappyNeon.apk"
echo "=============================================="
