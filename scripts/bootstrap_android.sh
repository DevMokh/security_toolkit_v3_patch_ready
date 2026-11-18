#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -f pubspec.yaml ]] || { echo "ERROR: pubspec.yaml not found at project root." >&2; exit 1; }
[[ -f lib/main.dart ]] || { echo "ERROR: lib/main.dart not found." >&2; exit 1; }
[[ -f android/app/src/main/AndroidManifest.xml ]] || { echo "ERROR: source AndroidManifest.xml is missing." >&2; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# Preserve app-owned source/configuration before regenerating only the Android platform.
for item in lib test assets; do
  if [[ -e "$item" ]]; then cp -a "$item" "$TMP_DIR/$item"; fi
done
for item in pubspec.yaml pubspec.lock analysis_options.yaml README.md; do
  if [[ -f "$item" ]]; then cp -a "$item" "$TMP_DIR/$item"; fi
done
cp -a android/app/src/main/AndroidManifest.xml "$TMP_DIR/AndroidManifest.xml"

rm -rf android
flutter create \
  --platforms=android \
  --org com.security \
  --project-name security_toolkit \
  --overwrite .

# Restore app-owned files exactly as they were.
for item in lib test assets; do
  if [[ -e "$TMP_DIR/$item" ]]; then
    rm -rf "$item"
    cp -a "$TMP_DIR/$item" "$item"
  fi
done
for item in pubspec.yaml pubspec.lock analysis_options.yaml README.md; do
  if [[ -f "$TMP_DIR/$item" ]]; then cp -a "$TMP_DIR/$item" "$item"; fi
done
cp -a "$TMP_DIR/AndroidManifest.xml" android/app/src/main/AndroidManifest.xml

# Set the exact Android application ID/namespace and minSdk in either Gradle DSL.
python3 - <<'PYCODE'
from pathlib import Path
import re

candidates = (Path('android/app/build.gradle.kts'), Path('android/app/build.gradle'))
found = False
for candidate in candidates:
    if not candidate.exists():
        continue
    found = True
    source = candidate.read_text(encoding='utf-8')
    if candidate.suffix == '.kts':
        source = re.sub(r'applicationId\s*=\s*["\'][^"\']+["\']', 'applicationId = "com.security.toolkit"', source, count=1)
        source = re.sub(r'namespace\s*=\s*["\'][^"\']+["\']', 'namespace = "com.security.toolkit"', source, count=1)
        source = re.sub(r'minSdk\s*=\s*(?:flutter\.minSdkVersion|\d+)', 'minSdk = 24', source, count=1)
    else:
        source = re.sub(r'applicationId\s+["\'][^"\']+["\']', 'applicationId "com.security.toolkit"', source, count=1)
        source = re.sub(r'namespace\s+["\'][^"\']+["\']', 'namespace "com.security.toolkit"', source, count=1)
        source = re.sub(r'minSdkVersion\s+(?:flutter\.minSdkVersion|\d+)', 'minSdkVersion 24', source, count=1)
    candidate.write_text(source, encoding='utf-8')
if not found:
    raise SystemExit('ERROR: app Gradle file was not generated.')
PYCODE

# Install exactly one V2 MainActivity. This avoids stale Java/Kotlin V1 entry points.
find android/app/src/main -type f \( -name 'MainActivity.kt' -o -name 'MainActivity.java' \) -delete
MAIN_DIR="android/app/src/main/kotlin/com/security/toolkit"
mkdir -p "$MAIN_DIR"
cat > "$MAIN_DIR/MainActivity.kt" <<'KOTLIN'
package com.security.toolkit

import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity()
KOTLIN

# Normalize the app manifest and explicitly mark Android embedding V2.
python3 scripts/repair_android_manifest.py

echo "Android platform generated. The workflow will verify V2 embedding next."
