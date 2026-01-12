import { useState, useRef, useEffect } from "react";
import chatAPI from "./api";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef(null);
  const userId = "abhi"; // keep same user to preserve memory

  // Auto-scroll to latest message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = input;
    setInput("");
    setError("");
    
    // Add user message
    setMessages(prev => [...prev, { sender: "user", text: userMessage }]);
    setLoading(true);

    try {
      const res = await chatAPI.post("/chat", {
        user_id: userId,
        message: userMessage
      });

      // Add bot response
      setMessages(prev => [
        ...prev,
        { sender: "bot", text: res.data.response }
      ]);
    } catch (err) {
      setError(err.message || "Failed to send message. Please try again.");
      console.error("Chat error:", err);
      
      // Add error message to chat
      setMessages(prev => [
        ...prev,
        { sender: "bot", text: "Sorry, I encountered an error. Please try again." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-box">
      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>Welcome to Nova Chatbot</h3>
            <p>Start a conversation to get started!</p>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.sender}`}>
            <div className="message-content">
              {m.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="msg bot">
            <div className="message-content loading">
              <span className="typing-indicator">
                <span></span><span></span><span></span>
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="input-area">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type a message... (Shift+Enter for new line)"
          rows="1"
          disabled={loading}
        />
        <button 
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="send-btn"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}