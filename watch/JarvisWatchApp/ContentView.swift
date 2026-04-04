import SwiftUI

struct ContentView: View {
    @EnvironmentObject var socketManager: SocketManager
    @State private var voiceInput = ""
    @State private var showingDictation = false
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Header Status
                HStack {
                    Circle()
                        .fill(socketManager.isConnected ? Color.green : Color.red)
                        .frame(width: 8, height: 8)
                    Text(socketManager.currentStatus)
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.gray)
                }
                .padding(.top, 4)
                
                // JARVIS HUD ORB
                ZStack {
                    Circle()
                        .stroke(Color.cyan.opacity(0.3), lineWidth: 2)
                        .frame(width: 80, height: 80)
                    
                    if socketManager.isReasoning {
                        Circle()
                            .fill(Color.purple.opacity(0.8))
                            .frame(width: 40, height: 40)
                            .shadow(color: .purple, radius: 10)
                    } else {
                        Circle()
                            .fill(Color.cyan.opacity(0.8))
                            .frame(width: 40, height: 40)
                            .shadow(color: .cyan, radius: 10)
                    }
                }
                .padding(.vertical, 8)
                
                // Voice Dictation Button (Native WatchOS Voice Input)
                Button(action: {
                    #if os(watchOS)
                    showingDictation = true
                    #endif
                }) {
                    HStack {
                        Image(systemName: "mic.fill")
                        Text(socketManager.isReasoning ? "Thinking..." : "Command")
                    }
                    .font(.system(size: 14, weight: .bold))
                }
                .tint(socketManager.isReasoning ? .purple : .cyan)
                .disabled(socketManager.isReasoning || !socketManager.isConnected)
                
                // ReAct Answer Output
                if let answer = socketManager.latestAnswer {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("JARVIS")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.cyan)
                        
                        Text(answer)
                            .font(.system(size: 13))
                            .multilineTextAlignment(.leading)
                    }
                    .padding()
                    .background(Color.black.opacity(0.5))
                    .cornerRadius(8)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Color.cyan.opacity(0.3), lineWidth: 1))
                }
            }
        }
        .onAppear {
            socketManager.connect()
        }
    }
}
