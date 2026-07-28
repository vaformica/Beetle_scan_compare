#!/bin/zsh
set -e

cd -- "$(dirname -- "$0")/.."

APP_NAME="Beetle Scan Compare"
DMG_NAME="Beetle-Scan-Compare-0.1.0-Apple-Silicon.dmg"
BUILD_ENV="${BUILD_ENV:-.venv-build}"
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"

if [[ ! -x "$BUILD_ENV/bin/pyinstaller" ]]; then
  echo "Missing $BUILD_ENV. Create it with Python 3.12 and install PyInstaller and Pillow."
  exit 1
fi

rm -rf build "dist/$APP_NAME.app" "dist/dmg-root" "$APP_NAME.spec"

"$BUILD_ENV/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --paths "$PWD" \
  --osx-bundle-identifier "org.beetlescan.compare" \
  --target-arch arm64 \
  packaging/macos_entry.py

mkdir -p "dist/dmg-root"
cp -R "dist/$APP_NAME.app" "dist/dmg-root/"
ln -s /Applications "dist/dmg-root/Applications"

rm -f "dist/$DMG_NAME"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "dist/dmg-root" \
  -ov \
  -format UDZO \
  "dist/$DMG_NAME"

echo "Created dist/$DMG_NAME"
