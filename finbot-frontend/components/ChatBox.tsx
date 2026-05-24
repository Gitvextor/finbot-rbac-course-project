"use client";
import { useAuth } from "../context/AuthContext";
import { KeyboardEvent, useState } from "react";
import MessageBubble from "./MessageBubble";
import { sendQuery } from "../lib/api";
import { Message } from "@/types";
import styles from "./ChatBot.module.css";

export default function ChatBox() {
    const { user, logout } = useAuth();

    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);

    const user_id = user?.user_id;
    const role = user?.role;

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        if (!user_id || !role) {
            alert("请先登录");
            return;
        }

        const query = input.trim();
        const newMessages: Message[] = [
            ...messages,
            { role: "user", content: query },
        ];

        setMessages(newMessages);
        setInput("");
        setLoading(true);

        try {
            const res = await sendQuery({
                user_id,
                role,
                query,
            });

            const botReply =
                res.answer ||
                res.block_reason ||
                "⚠️ 请求异常，请稍后重试";

            setMessages([
                ...newMessages,
                { role: "assistant", content: botReply },
            ]);
        } catch {
            setMessages([
                ...newMessages,
                {
                    role: "assistant",
                    content: "❌ 无法连接服务器，请确认后端已启动",
                },
            ]);
        }

        setLoading(false);
    };

    const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void handleSend();
        }
    };

    return (
        <div className={styles.chatbox}>
            <div className={styles.chatboxHeader}>
                <span>FinBot 💼</span>
                <button onClick={logout} className={styles.logoutBtn}>
                    退出
                </button>
            </div>

            <div className={styles.chatboxMessages}>
                {messages.map((msg, i) => (
                    <MessageBubble key={i} message={msg} />
                ))}
                {loading && (
                    <p className={styles.thinking}>
                        思考中… 首次提问可能需要 1–2 分钟构建知识库
                    </p>
                )}
            </div>

            <div className={styles.chatboxInput}>
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入问题（Enter 发送，Shift+Enter 换行）"
                    rows={3}
                />
                <button onClick={() => void handleSend()} disabled={loading}>
                    发送
                </button>
            </div>
        </div>
    );
}
