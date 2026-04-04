#!/bin/bash
rm -rf ~/Desktop/JARVIS.app
mkdir -p ~/Desktop/JARVIS.app/Contents/MacOS
mkdir -p ~/Desktop/JARVIS.app/Contents/Resources

cp -R /Applications/AZAN/dist/JARVIS/* ~/Desktop/JARVIS.app/Contents/MacOS/

cat << 'PLIST_EOF' > ~/Desktop/JARVIS.app/Contents/Info.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>JARVIS</string>
    <key>CFBundleIdentifier</key>
    <string>com.azan.jarvis</string>
    <key>CFBundleName</key>
    <string>JARVIS</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>JARVIS needs your microphone to hear your voice commands.</string>
</dict>
</plist>
PLIST_EOF

plutil -convert xml1 ~/Desktop/JARVIS.app/Contents/Info.plist
xattr -cr ~/Desktop/JARVIS.app
