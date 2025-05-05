import { useState, useEffect, useRef } from "react";
import styles from "../styles/ChatUI.module.css";
import { X, Minus, Maximize2 } from "lucide-react";

/**
 * Chatbot component for McBot’s front‑end.
 * The back‑end base URL is injected at build time through
 * NEXT_PUBLIC_API_URL (set in Render’s env‑vars).
 */
export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(true);
  const [isLarge, setIsLarge] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [conversationContext, setConversationContext] = useState({});

  const chatBoxRef = useRef(null);

  // Always scroll to the latest message
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------
  const API_BASE =
    (process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000").replace(/\/$/, "");

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;

    // Show user message immediately
    setMessages((prev) => [...prev, { text: trimmed, sender: "customer" }]);
    setInput("");

    console.log("API_BASE =", API_BASE);
    try {
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmed,
          context: conversationContext,
        }),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        console.error("Error response body:", errText);
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setMessages((prev) => [...prev, { text: data.reply, sender: "bot" }]);
      if (data.context) setConversationContext(data.context);
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => [
        ...prev,
        { text: "Sorry, something went wrong. Please try again.", sender: "bot" },
      ]);
    }
  };

  // ------------------------------------------------------------------
  // UI
  // ------------------------------------------------------------------
  return (
    <div
      className={`${styles.chatContainer} ${isLarge ? styles.large : ""} ${
        isOpen ? "" : styles.hidden
      }`}
    >
      {/* Top bar */}
      <div className={styles.topBar}>
        McBot
        <div className={styles.buttons}>
          <X className={styles.icon} onClick={() => setIsOpen(false)} />
          <Maximize2 className={styles.icon} onClick={() => setIsLarge((s) => !s)} />
          <Minus className={styles.icon} onClick={() => setIsOpen((s) => !s)} />
        </div>
      </div>

      {/* Chat history */}
      <div className={styles.chatBox} ref={chatBoxRef}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={msg.sender === "customer" ? styles.customerMessage : styles.botMessage}
          >
            {msg.text}
          </div>
        ))}
      </div>

      {/* Input area */}
      <div className={styles.inputArea}>
        <input
          type="text"
          className={styles.chatInput}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type a message…"
        />
        <button className={styles.sendButton} onClick={sendMessage}>
          ➢
        </button>
      </div>
    </div>
  );
}
