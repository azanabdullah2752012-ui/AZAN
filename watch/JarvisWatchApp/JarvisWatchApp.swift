import SwiftUI

@main
struct JarvisWatchApp: App {
    @StateObject private var socketManager = SocketManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(socketManager)
        }
    }
}
