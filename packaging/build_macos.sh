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

rm -rf build "dist/$APP_NAME.app" "$APP_NAME.spec"

"$BUILD_ENV/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --paths "$PWD" \
  --osx-bundle-identifier "org.beetlescan.compare" \
  --target-arch arm64 \
  packaging/macos_entry.py

STAGING_DIR="$(mktemp -d /private/tmp/beetle-scan-dmg.XXXXXX)"
if [[ "$STAGING_DIR" != /private/tmp/beetle-scan-dmg.* ]]; then
  echo "Unexpected DMG staging path: $STAGING_DIR"
  exit 1
fi

# -X prevents Dropbox/Finder extended attributes from invalidating signing.
cp -R -X "dist/$APP_NAME.app" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"
codesign --force --deep --sign - "$STAGING_DIR/$APP_NAME.app"
codesign --verify --deep --strict "$STAGING_DIR/$APP_NAME.app"

rm -f "dist/$DMG_NAME"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "dist/$DMG_NAME"

echo "Created dist/$DMG_NAME"
