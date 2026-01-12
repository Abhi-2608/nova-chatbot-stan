import { useState } from "react";
import Chat from "./Chat";
import "./App.css";

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="app">
      <header className="app-header">
        <button 
          className="toggle-sidebar"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        >
          ☰
        </button>
        <h1>Nova Chatbot</h1>
        <div className="header-spacer"></div>
      </header>

      <div className="app-container">
        {isSidebarOpen && (
          <aside className="sidebar">
            <div className="sidebar-content">
              {/* Welcome Card */}
              <div className="welcome-card">
                <div className="love-sticker">💜</div>
                <h2>Chat with Nova</h2>
                <p className="created-by">Created by Abhishek</p>
                <p className="tagline">Your true personalized chatbot</p>
                <div className="sticker-row">
                  <span className="sticker">😊</span>
                  <span className="sticker">🤖</span>
                  <span className="sticker">💬</span>
                </div>
              </div>

              {/* New Chat Button */}
              <button className="new-chat-btn">+ New Chat</button>

              {/* Chat History */}
              <div className="chat-history">
                <h3>Chat History</h3>
                <div className="history-empty">
                  <p>No chats yet</p>
                </div>
              </div>

              {/* Footer */}
              <div className="sidebar-footer">
                <p>Made with 💜 for you</p>
              </div>
            </div>
          </aside>
        )}

        <main className="chat-container">
          <Chat />
        </main>

        {/* Right Side Decoration */}
        <aside className="right-decoration">
          <div className="decoration-content">
            <div className="floating-icon icon-1">🤖</div>
            <div className="floating-icon icon-2">💬</div>
            <div className="floating-icon icon-3">✨</div>
            <div className="floating-icon icon-4">💡</div>
            <div className="floating-icon icon-5">🎯</div>
            
            <div className="decoration-text">
              <h3>Powered by Nova</h3>
              <p>Your AI assistant that learns and understands you</p>
            </div>

            <div className="decoration-features">
              <div className="feature-item">
                <span className="feature-icon">⚡</span>
                <span>Lightning Fast</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🧠</span>
                <span>Smart AI</span>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔒</span>
                <span>Secure Chat</span>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default App;