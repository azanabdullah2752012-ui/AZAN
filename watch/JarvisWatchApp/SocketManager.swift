import Foundation
import Combine
import WatchKit

class SocketManager: ObservableObject {
    @Published var isConnected = false
    @Published var currentStatus = "Disconnected"
    @Published var latestAnswer: String?
    @Published var isReasoning = false
    
    private var webSocketTask: URLSessionWebSocketTask?
    
    // Replace with your Mac's local IP Address
    private let macIP = "192.168.1.100" 
    private let deviceToken = "JARVIS-WATCH-001"
    
    func connect() {
        guard let url = URL(string: "ws://\\(macIP):8000/api/mobile/ws/\\(deviceToken)") else { return }
        
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()
        
        receiveMessage()
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        isConnected = false
        currentStatus = "Disconnected"
    }
    
    func sendCommand(_ command: String) {
        let payload: [String: Any] = ["type": "command", "text": command]
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let jsonString = String(data: data, encoding: .utf8) else { return }
        
        let message = URLSessionWebSocketTask.Message.string(jsonString)
        webSocketTask?.send(message) { error in
            if let error = error {
                print("Watch send error: \\(error)")
            } else {
                DispatchQueue.main.async {
                    self.isReasoning = true
                    self.latestAnswer = nil
                    WKInterfaceDevice.current().play(.success)
                }
            }
        }
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .failure(let error):
                print("Watch socket error: \\(error)")
                DispatchQueue.main.async {
                    self?.isConnected = false
                    self?.currentStatus = "Error connecting"
                }
                
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleMessage(text)
                default: break
                }
                self?.receiveMessage()
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
        
        DispatchQueue.main.async {
            let type = json["type"] as? String ?? ""
            
            if type == "system" {
                self.isConnected = true
                self.currentStatus = "Connected to Mac"
                WKInterfaceDevice.current().play(.click)
            } 
            else if type == "state_stream" {
                if let payload = json["data"] as? [String: Any] {
                    if let answer = payload["answer"] as? String {
                        self.latestAnswer = answer
                        self.isReasoning = false
                        WKInterfaceDevice.current().play(.notification)
                    }
                }
            }
            else if type == "ack" {
                self.currentStatus = "Executing..."
            }
        }
    }
}
