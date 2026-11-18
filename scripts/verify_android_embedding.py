#!/usr/bin/env python3
"""Verify the exact Android manifest condition used by Flutter's V1/V2 check."""
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
root_dir = Path.cwd()
manifest = root_dir / "android/app/src/main/AndroidManifest.xml"
if not manifest.is_file():
    raise SystemExit(
        "ERROR: AndroidManifest.xml is missing at the Flutter repository root: "
        f"{manifest}"
    )

try:
    document = ET.parse(manifest).getroot()
except ET.ParseError as exc:
    raise SystemExit(f"ERROR: AndroidManifest.xml is invalid XML: {exc}")

applications = document.findall("application")
if len(applications) != 1:
    raise SystemExit(
        f"ERROR: Expected exactly one <application>; found {len(applications)} in {manifest}"
    )
application = applications[0]
legacy_name = application.get(f"{{{ANDROID}}}name")
if legacy_name == "io.flutter.app.FlutterApplication":
    raise SystemExit("ERROR: V1 FlutterApplication remains in AndroidManifest.xml.")

embedding_values = [
    node.get(f"{{{ANDROID}}}value")
    for node in application.findall("meta-data")
    if node.get(f"{{{ANDROID}}}name") == "flutterEmbedding"
]
if embedding_values != ["2"]:
    raise SystemExit(
        "ERROR: Flutter requires exactly one <meta-data android:name=\"flutterEmbedding\" "
        f"android:value=\"2\"/> entry; found values {embedding_values!r} in {manifest}"
    )

activity = root_dir / "android/app/src/main/kotlin/com/security/toolkit/MainActivity.kt"
if not activity.is_file():
    raise SystemExit(f"ERROR: V2 MainActivity source missing: {activity}")
source = activity.read_text(encoding="utf-8")
if "io.flutter.embedding.android.FlutterActivity" not in source or "class MainActivity : FlutterActivity()" not in source:
    raise SystemExit("ERROR: MainActivity is not using the V2 FlutterActivity API.")

print("ANDROID EMBEDDING CHECK: PASS")
print(f"Project root: {root_dir}")
print(f"Manifest: {manifest}")
print(f"Embedding metadata: {embedding_values}")
print(f"MainActivity: {activity}")
