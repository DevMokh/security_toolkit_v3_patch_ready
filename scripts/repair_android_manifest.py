#!/usr/bin/env python3
"""Normalize AndroidManifest.xml to Flutter Android embedding V2."""
from pathlib import Path
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID)
manifest_path = Path("android/app/src/main/AndroidManifest.xml")
if not manifest_path.is_file():
    raise SystemExit(f"ERROR: Android manifest not found: {manifest_path.resolve()}")

try:
    tree = ET.parse(manifest_path)
except ET.ParseError as exc:
    raise SystemExit(f"ERROR: Invalid AndroidManifest.xml: {exc}")

root = tree.getroot()
android_name = f"{{{ANDROID}}}name"
android_value = f"{{{ANDROID}}}value"

permissions = {
    element.get(android_name)
    for element in root.findall("uses-permission")
}
for permission in ("android.permission.INTERNET", "android.permission.CAMERA"):
    if permission not in permissions:
        ET.SubElement(root, "uses-permission", {android_name: permission})

application = root.find("application")
if application is None:
    raise SystemExit("ERROR: Android manifest has no <application> element.")

if application.get(android_name) == "io.flutter.app.FlutterApplication":
    application.set(android_name, "${applicationName}")
application.set(f"{{{ANDROID}}}label", "Security Toolkit")
application.set(f"{{{ANDROID}}}usesCleartextTraffic", "false")

# Flutter checks each matching metadata element; remove duplicates so a stale
# value="1" cannot remain beside the valid value="2" entry.
embedding_nodes = [
    node for node in application.findall("meta-data")
    if node.get(android_name) == "flutterEmbedding"
]
if embedding_nodes:
    embedding = embedding_nodes[0]
    for duplicate in embedding_nodes[1:]:
        application.remove(duplicate)
else:
    embedding = ET.SubElement(application, "meta-data")
embedding.set(android_name, "flutterEmbedding")
embedding.set(android_value, "2")

for item in list(application.findall("meta-data")):
    if item.get(android_name) == "io.flutter.app.android.SplashScreenUntilFirstFrame":
        application.remove(item)

tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
print(f"Normalized {manifest_path.resolve()}: exactly one flutterEmbedding=2")
