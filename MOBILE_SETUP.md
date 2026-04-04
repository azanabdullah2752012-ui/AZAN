# J.A.R.V.I.S. Mobile & Watch Companion Setup

Welcome to Phase 18. You now have the source code for a fully synchronized multi-device J.A.R.V.I.S. ecosystem.

## 🖥 1. Start the Mac Backend
The foundation of JARVIS is your Mac backend. It holds the memory, executes tools, and processes voice.
Ensure it is running:
```bash
cd /Applications/AZAN
./start_jarvis.sh
```
Find your Mac's Local IP address (e.g., `192.168.1.100`) via System Settings > Network.

---

## 📱 2. Running the Mobile App (iOS / Android)

The mobile app is an Expo React Native project located at `/Applications/AZAN/mobile`.

### Prerequisites
1. Install the **Expo Go** app on your iPhone or Android device from the App Store/Google Play.
2. Ensure your phone is on the **same Wi-Fi network** as your Mac.

### Configuration
1. Open `/Applications/AZAN/mobile/App.js` in a code editor.
2. Find line 9 and replace with your actual Mac IP Address (I have already set this to your current IP):
   ```javascript
   const MAC_IP = '192.168.0.8'; 
   ```

### Installation & Launch
Open your Mac terminal:
```bash
cd /Applications/AZAN/mobile
# Install required animation libraries
npx expo install react-native-reanimated

# Start the Expo development server
npx expo start
```
A huge QR code will appear in your terminal. 
- **iOS:** Open your Camera app and scan the QR code to launch in Expo Go.
- **Android:** Open the Expo Go app and tap "Scan QR Code".

You will instantly see the Cinematic JARVIS HUD syncing with your Mac.

---

## ⌚️ 3. Running the Watch Companion (WatchOS)

The Apple Watch companion is built in native SwiftUI, located at `/Applications/AZAN/watch/JarvisWatchApp`.

### Prerequisites
1. Open **Xcode** on your Mac.

### Configuration & Launch
1. In Xcode, click `File > Open...` and select the folder `/Applications/AZAN/watch/JarvisWatchApp`.
2. Open `SocketManager.swift`.
3. Locate line 13 and replace the placeholder with your Mac's Local IP:
   ```swift
   private let macIP = "192.168.1.xxx" 
   ```
4. Connect your physical Apple Watch (or use the Watch Simulator).
5. Press the **Play (Build and Run)** button in Xcode.

The WatchOS app will deploy, present the JARVIS HUD, and await dictation commands.

---

## 🔒 Security Notes
- ReAct loops map 1:1. Only one device can dictate commands at a time to prevent orchestrator confusion.
- All tasks flow through the Mac's Local LLMs. Your device acts purely as a dumb terminal streaming UI commands back and forth over WebSocket. No data leaves your network.
