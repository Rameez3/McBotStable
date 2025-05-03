import { useState, useEffect, useRef } from "react"; // Import useEffect and useRef
import styles from "../styles/ChatUI.module.css";
import { X, Minus, Maximize2 } from "lucide-react";

export default function Chatbot() {
    const [isOpen, setIsOpen] = useState(true);
    const [isLarge, setIsLarge] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [conversationContext, setConversationContext] = useState({});

    // Create a ref for the chatbox div
    const chatBoxRef = useRef(null);

    // useEffect hook to scroll to bottom when messages change
    useEffect(() => {
        if (chatBoxRef.current) {
            // Smooth scrolling option:
            // chatBoxRef.current.scrollTo({ top: chatBoxRef.current.scrollHeight, behavior: 'smooth' });

            // Immediate scrolling:
            chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
        }
    }, [messages]); // Dependency array: run this effect when messages state updates

    const sendMessage = async () => {
        if (input.trim() !== "") {
            const userMessage = { text: input, sender: "customer" };
            // Update messages immediately for user feedback
            setMessages(prevMessages => [...prevMessages, userMessage]);
            const currentInput = input;
            setInput("");

            try {
                const response = await fetch('/api/chat', { // Ensure this matches your backend URL (e.g., http://localhost:8000/api/chat if backend is on port 8000)
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    // Pass the *latest* messages context, including the user's just-sent message, if needed by the bot logic
                    // For now, passing the context *before* the user message was added. Adjust if needed.
                    body: JSON.stringify({ message: currentInput, context: conversationContext }),
                });

                if (!response.ok) {
                     // Log the error response body for more details if available
                     const errorBody = await response.text();
                     console.error("Error response body:", errorBody);
                     throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                // Add the bot's reply
                setMessages((prevMessages) => [
                    ...prevMessages,
                    { text: data.reply, sender: "bot" }
                ]);

                if (data.context) {
                    setConversationContext(data.context);
                }

            } catch (error) {
                console.error("Failed to send message:", error);
                // Display error message in chat
                setMessages((prevMessages) => [
                    ...prevMessages,
                    { text: `Sorry, error connecting to bot: ${error.message}. Check console for details.`, sender: "bot" }
                ]);
            }
        }
    };

    return (
        <div className={`${styles.chatContainer} ${isLarge ? styles.large : ""} ${isOpen ? "" : styles.hidden}`}>
            {/* Top Bar */}
            <div className={styles.topBar}>
                McBot
                <div className={styles.buttons}>
                    <X className={styles.icon} onClick={() => setIsOpen(false)} />
                    <Maximize2 className={styles.icon} onClick={() => setIsLarge(!isLarge)} />
                    <Minus className={styles.icon} onClick={() => setIsOpen(false)} /> {/* Consider making this minimize instead of close */}
                </div>
            </div>

            {/* Chat Box - Add the ref here */}
            <div className={styles.chatBox} ref={chatBoxRef}>
                {messages.map((msg, index) => (
                    <div key={index} className={msg.sender === "customer" ? styles.customerMessage : styles.botMessage}>
                        {msg.text}
                    </div>
                ))}
            </div>

            {/* Typing Area */}
            <div className={styles.inputContainer}>
                <input
                    type="text"
                    className={styles.chatInput}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                    placeholder="Type a message..."
                />
                <button className={styles.sendButton} onClick={sendMessage}>
                    ➢
                </button>
            </div>
        </div>
    );
}