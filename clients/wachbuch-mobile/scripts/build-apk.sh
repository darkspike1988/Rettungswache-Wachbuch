#!/usr/bin/env bash
# Build a sideloadable release APK for Wachbuch Mobile (AGPL).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export ANDROID_HOME="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"

flutter pub get
flutter test
flutter build apk --release

mkdir -p dist
cp -f build/app/outputs/flutter-apk/app-release.apk dist/wachbuch-mobile.apk
ls -lh dist/wachbuch-mobile.apk
echo "APK ready: $ROOT/dist/wachbuch-mobile.apk"
