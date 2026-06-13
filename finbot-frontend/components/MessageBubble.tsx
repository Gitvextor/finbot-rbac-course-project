import { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import styles from "./MessageBubble.module.css";

export default function MessageBubble({ message }: { message: Message }) {
    const isUser = message.role === "user";

    return (
        <div className={`${styles.messageRow} ${isUser ? styles.user : styles.assistant}`}>
            <div className={styles.messageBubble}>
                {isUser ? (
                    message.content
                ) : (
                    <div className={styles.markdown}>
                        <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                )}
            </div>
        </div>
    );
}
