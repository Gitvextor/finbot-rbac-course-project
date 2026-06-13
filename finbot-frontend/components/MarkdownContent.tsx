import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { normalizeMarkdown } from "@/lib/normalizeMarkdown";
import styles from "./MarkdownContent.module.css";

type MarkdownContentProps = {
    content: string;
    className?: string;
};

export default function MarkdownContent({ content, className }: MarkdownContentProps) {
    return (
        <div className={[styles.markdown, className].filter(Boolean).join(" ")}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {normalizeMarkdown(content)}
            </ReactMarkdown>
        </div>
    );
}
