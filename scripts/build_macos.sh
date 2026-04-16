#!/bin/bash

set -euo pipefail

CLI_ONLY=0
SIGN_BUILD=0
NOTARIZE_BUILD=0
CREATE_RELEASE_ASSETS=0
CREATE_DMG=1

APP_NAME="TexturesTool"
CLI_NAME="TexturesToolCLI"
DEFAULT_BUNDLE_ID="com.yimeng.texturetools"

usage() {
  cat <<'EOF'
Usage:
  ./build_macos.sh [options]

Options:
  --cli-only        Build only the CLI binary.
  --sign            Codesign macOS artifacts with Developer ID.
  --notarize        Submit signed artifacts to Apple notarization.
  --release         Build, sign, notarize, staple, and export release assets.
  --release-assets  Export zip/dmg release assets without notarization.
  --skip-dmg        Skip DMG creation when exporting release assets.
  --bundle-id ID    Override the app bundle identifier.
  --help            Show this message.

Environment for signing/notarization:
  APPLE_SIGN_IDENTITY   Developer ID Application certificate name.
  APPLE_NOTARY_PROFILE  Keychain profile configured for xcrun notarytool.
  APPLE_BUNDLE_ID       Optional override for the app bundle identifier.

Examples:
  ./build_macos.sh
  ./build_macos.sh --cli-only
  ./build_macos.sh --release
  APPLE_SIGN_IDENTITY="Developer ID Application: Example (TEAMID)" \
  APPLE_NOTARY_PROFILE="notary-profile" \
  ./build_macos.sh --release
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cli-only)
      CLI_ONLY=1
      ;;
    --sign)
      SIGN_BUILD=1
      ;;
    --notarize)
      SIGN_BUILD=1
      NOTARIZE_BUILD=1
      CREATE_RELEASE_ASSETS=1
      ;;
    --release)
      SIGN_BUILD=1
      NOTARIZE_BUILD=1
      CREATE_RELEASE_ASSETS=1
      ;;
    --release-assets)
      CREATE_RELEASE_ASSETS=1
      ;;
    --skip-dmg)
      CREATE_DMG=0
      ;;
    --bundle-id)
      shift
      if [[ $# -eq 0 ]]; then
        echo "--bundle-id requires a value."
        exit 1
      fi
      DEFAULT_BUNDLE_ID="$1"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo
      usage
      exit 1
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_ROOT/dist"
BUILD_DIR="$PROJECT_ROOT/build"
SPEC_DIR="$PROJECT_ROOT/spec"
SRC_DIR="$PROJECT_ROOT/src"
RELEASE_DIR="$PROJECT_ROOT/release_assets"
STAGING_DIR="$BUILD_DIR/release_staging"
APP_BUNDLE_ID="${APPLE_BUNDLE_ID:-$DEFAULT_BUNDLE_ID}"

cd "$PROJECT_ROOT"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1"
    exit 1
  fi
}

require_var() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "Required environment variable is missing: $var_name"
    exit 1
  fi
}

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 is required but was not found."
  exit 1
fi

require_command xcrun
require_command codesign
require_command ditto
require_command hdiutil

if [[ "$SIGN_BUILD" -eq 1 ]]; then
  require_var APPLE_SIGN_IDENTITY
fi

if [[ "$NOTARIZE_BUILD" -eq 1 ]]; then
  require_var APPLE_NOTARY_PROFILE
fi

"$PYTHON_BIN" -m pip install -r requirements.txt

rm -rf "$BUILD_DIR" "$SPEC_DIR"
mkdir -p "$DIST_DIR"

COMMON_ARGS=(
  --noconfirm
  --clean
  --distpath "$DIST_DIR"
  --workpath "$BUILD_DIR"
  --specpath "$SPEC_DIR"
  --paths "$SRC_DIR"
  --collect-submodules textures_tool
)

if [[ "$CLI_ONLY" -eq 0 ]]; then
  "$PYTHON_BIN" -m PyInstaller \
    "${COMMON_ARGS[@]}" \
    --name "$APP_NAME" \
    --windowed \
    --osx-bundle-identifier "$APP_BUNDLE_ID" \
    texture_resize_gui.py
fi

"$PYTHON_BIN" -m PyInstaller \
  "${COMMON_ARGS[@]}" \
  --name "$CLI_NAME" \
  --console \
  texture_resize_tool.py

APP_PATH="$DIST_DIR/$APP_NAME.app"
CLI_PATH="$DIST_DIR/$CLI_NAME"
APP_ZIP_PATH="$RELEASE_DIR/${APP_NAME}-macOS.zip"
CLI_ZIP_PATH="$RELEASE_DIR/${CLI_NAME}-macOS.zip"
DMG_PATH="$RELEASE_DIR/${APP_NAME}-macOS.dmg"

sign_bundle() {
  local target_path="$1"
  local identifier="$2"

  echo "Signing $target_path"
  codesign \
    --force \
    --deep \
    --options runtime \
    --timestamp \
    --sign "$APPLE_SIGN_IDENTITY" \
    --identifier "$identifier" \
    "$target_path"
}

sign_file() {
  local target_path="$1"
  local identifier="$2"

  echo "Signing $target_path"
  codesign \
    --force \
    --options runtime \
    --timestamp \
    --sign "$APPLE_SIGN_IDENTITY" \
    --identifier "$identifier" \
    "$target_path"
}

verify_bundle_signature() {
  local target_path="$1"

  codesign --verify --deep --strict --verbose=2 "$target_path"
}

verify_file_signature() {
  local target_path="$1"

  codesign --verify --strict --verbose=2 "$target_path"
}

create_zip() {
  local source_path="$1"
  local output_path="$2"

  rm -f "$output_path"
  ditto -c -k --keepParent "$source_path" "$output_path"
}

submit_for_notarization() {
  local artifact_path="$1"

  echo "Submitting $artifact_path for notarization"
  xcrun notarytool submit "$artifact_path" \
    --keychain-profile "$APPLE_NOTARY_PROFILE" \
    --wait
}

create_dmg() {
  local source_app="$1"
  local output_dmg="$2"
  local dmg_root="$STAGING_DIR/dmg_root"

  rm -rf "$dmg_root"
  mkdir -p "$dmg_root"
  cp -R "$source_app" "$dmg_root/"

  rm -f "$output_dmg"
  hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$dmg_root" \
    -ov \
    -format UDZO \
    "$output_dmg"
}

if [[ "$SIGN_BUILD" -eq 1 ]]; then
  if [[ "$CLI_ONLY" -eq 0 ]]; then
    sign_bundle "$APP_PATH" "$APP_BUNDLE_ID"
    verify_bundle_signature "$APP_PATH"
  fi

  sign_file "$CLI_PATH" "$APP_BUNDLE_ID.cli"
  verify_file_signature "$CLI_PATH"
fi

if [[ "$CREATE_RELEASE_ASSETS" -eq 1 ]]; then
  rm -rf "$RELEASE_DIR" "$STAGING_DIR"
  mkdir -p "$RELEASE_DIR" "$STAGING_DIR"

  if [[ "$NOTARIZE_BUILD" -eq 1 ]]; then
    if [[ "$CLI_ONLY" -eq 0 ]]; then
      local_app_notary_zip="$STAGING_DIR/${APP_NAME}-notary.zip"
      create_zip "$APP_PATH" "$local_app_notary_zip"
      submit_for_notarization "$local_app_notary_zip"
      xcrun stapler staple "$APP_PATH"
    fi

    create_zip "$CLI_PATH" "$CLI_ZIP_PATH"
    submit_for_notarization "$CLI_ZIP_PATH"
  fi

  if [[ "$CLI_ONLY" -eq 0 ]]; then
    create_zip "$APP_PATH" "$APP_ZIP_PATH"

    if [[ "$CREATE_DMG" -eq 1 ]]; then
      create_dmg "$APP_PATH" "$DMG_PATH"

      if [[ "$SIGN_BUILD" -eq 1 ]]; then
        sign_file "$DMG_PATH" "$APP_BUNDLE_ID.dmg"
        verify_file_signature "$DMG_PATH"
      fi

      if [[ "$NOTARIZE_BUILD" -eq 1 ]]; then
        submit_for_notarization "$DMG_PATH"
        xcrun stapler staple "$DMG_PATH"
      fi
    fi
  fi

  if [[ "$NOTARIZE_BUILD" -eq 0 ]]; then
    create_zip "$CLI_PATH" "$CLI_ZIP_PATH"
  fi
fi

echo
echo "Build complete."
echo "Artifacts:"
if [[ "$CLI_ONLY" -eq 0 ]]; then
  echo "  GUI app: $APP_PATH"
fi
echo "  CLI binary: $CLI_PATH"
if [[ "$CREATE_RELEASE_ASSETS" -eq 1 ]]; then
  if [[ "$CLI_ONLY" -eq 0 ]]; then
    echo "  GUI zip: $APP_ZIP_PATH"
    if [[ "$CREATE_DMG" -eq 1 ]]; then
      echo "  GUI dmg: $DMG_PATH"
    fi
  fi
  echo "  CLI zip: $CLI_ZIP_PATH"
fi
