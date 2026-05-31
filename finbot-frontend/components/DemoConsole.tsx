"use client";

import { KeyboardEvent, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useAuth } from "../context/AuthContext";
import { getAccessibleDocuments, sendQuery } from "../lib/api";
import { AuthUser, DocumentRecord, Message } from "@/types";
import styles from "./DemoConsole.module.css";

const roleScopes: Record<string, string> = {
    c_level: "可查看全部课程资料与归档",
    engineering: "可查看教学资料、评分标准与公开资料",
    hr_manager: "可查看授权的隐私类资料与公开资料",
    marketing: "可查看公开资料",
    employee: "只能查看公开课程资料",
};

const roleViews: Record<string, {
    title: string;
    subtitle: string;
    scope: string[];
    suggestedQuestions: string[];
    helperText: string;
}> = {
    admin: {
        title: "管理员资料助手",
        subtitle: "用于总览课程资料、维护归档、查看答案文件、评分标准和系统访问边界。",
        scope: ["全部资料库", "教师答案", "评分标准", "隐私资料", "公开资料"],
        suggestedQuestions: [
            "What documents are available in this course archive?",
            "Summarize the grading rubric for this project",
            "Explain the RBAC policy for student access",
            "What should be shown in the final demo?",
        ],
        helperText: "Admin 视角用于最终验收：可以确认资料是否齐全，并演示不同角色下可见内容不同。",
    },
    teacher: {
        title: "教师资料助手",
        subtitle: "用于查询教师答案、评分标准、课程归档和公开说明。",
        scope: ["教师答案", "评分标准", "课程归档", "公开资料"],
        suggestedQuestions: [
            "Summarize the teacher answer key",
            "What are the grading criteria for this project?",
            "Which materials can students access?",
            "Explain how the demo proves RBAC works",
        ],
        helperText: "Teacher 可以查看受限教学资料；学生使用同样问题时应被系统拒绝或只返回公开资料。",
    },
    ta: {
        title: "助教资料助手",
        subtitle: "用于查询评分标准、实现说明、课程归档和公开材料。",
        scope: ["评分标准", "工程说明", "课程归档", "公开资料"],
        suggestedQuestions: [
            "What are the grading criteria for this project?",
            "Explain the CI/CD pipeline for the project",
            "What is the SLA for our API uptime?",
            "Which parts should be captured in screenshots?",
        ],
        helperText: "TA 视角强调评分协助和工程资料，不默认开放教师答案或隐私资料。",
    },
    student: {
        title: "学生公开资料助手",
        subtitle: "用于查询公开课程说明、演示流程和允许学生查看的资料。",
        scope: ["公开资料"],
        suggestedQuestions: [
            "What documents can students access?",
            "What is the course project about?",
            "How should I use this assistant?",
            "Summarize the public syllabus",
        ],
        helperText: "Student 只能访问公开资料；答案文件、评分标准和隐私资料会被拒绝。",
    },
};

function getRoleView(user: AuthUser) {
    const label = user.label?.toLowerCase() ?? "";
    if (user.is_admin || user.chat_role === "c_level") return roleViews.admin;
    if (label.includes("teacher")) return roleViews.teacher;
    if (label.includes("ta")) return roleViews.ta;
    return roleViews.student;
}

function formatDocumentName(filename: string) {
    return filename
        .replace(/\.(md|csv|txt|pdf|docx)$/i, "")
        .replaceAll("_", " ");
}

export default function DemoConsole() {
    const { user, logout } = useAuth();
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [documents, setDocuments] = useState<DocumentRecord[]>([]);
    const [documentsLoading, setDocumentsLoading] = useState(false);
    const [documentsError, setDocumentsError] = useState("");
    const [loading, setLoading] = useState(false);

    const roleText = useMemo(() => {
        if (!user) return "";
        return `${user.label ?? user.username} / ${user.department} / ${user.level}`;
    }, [user]);
    const roleView = useMemo(() => (user ? getRoleView(user) : roleViews.student), [user]);

    const loadDocuments = useCallback(async () => {
        if (!user?.token) return;
        setDocumentsLoading(true);
        setDocumentsError("");
        try {
            const result = await getAccessibleDocuments(user.token);
            setDocuments(result);
        } catch (err) {
            setDocumentsError(err instanceof Error ? err.message : "无法读取资料归档");
        } finally {
            setDocumentsLoading(false);
        }
    }, [user?.token]);

    useEffect(() => {
        void loadDocuments();
    }, [loadDocuments]);

    if (!user) return null;

    const submitQuery = async (query = input) => {
        if (!query.trim() || loading) return;

        const cleanQuery = query.trim();
        const nextMessages: Message[] = [...messages, { role: "user", content: cleanQuery }];
        setMessages(nextMessages);
        setInput("");
        setLoading(true);

        try {
            const response = await sendQuery({
                user_id: user.username,
                role: user.chat_role,
                query: cleanQuery,
                session_id: `${user.username}_assistant`,
            });
            const answer =
                response.answer ||
                response.block_reason ||
                response.detail ||
                "请求已处理，但没有返回可展示内容。";

            setMessages([...nextMessages, { role: "assistant", content: answer, meta: response }]);
        } catch (err) {
            setMessages([
                ...nextMessages,
                {
                    role: "assistant",
                    content: err instanceof Error ? err.message : "无法连接后端服务",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void submitQuery();
        }
    };

    return (
        <main className={styles.shell}>
            <aside className={styles.sidebar}>
                <div>
                    <p className={styles.eyebrow}>FinBot Assistant</p>
                    <h1>{roleView.title}</h1>
                    <p className={styles.subtitle}>{roleView.subtitle}</p>
                </div>

                <div className={styles.userPanel}>
                    <span>当前身份</span>
                    <strong>{roleText}</strong>
                    <small>{roleScopes[user.chat_role] ?? "按当前身份访问资料"}</small>
                </div>

                <section className={styles.scopePanel}>
                    <h2>当前可见范围</h2>
                    <div>
                        {roleView.scope.map((item) => (
                            <span key={item}>{item}</span>
                        ))}
                    </div>
                </section>

                <section className={styles.assistantPanel}>
                    <h2>可以问</h2>
                    {roleView.suggestedQuestions.map((question) => (
                        <button
                            key={question}
                            onClick={() => {
                                setInput(question);
                                void submitQuery(question);
                            }}
                            disabled={loading}
                        >
                            {question}
                        </button>
                    ))}
                </section>

                <section className={styles.assistantPanel}>
                    <h2>权限说明</h2>
                    <p>{roleView.helperText}</p>
                </section>

                <button className={styles.logoutButton} onClick={logout}>
                    切换身份
                </button>
            </aside>

            <section className={styles.assistantContent}>
                <header className={styles.assistantHeader}>
                    <div>
                        <p className={styles.eyebrow}>Secure RAG Chat</p>
                        <h2>{roleView.title}</h2>
                    </div>
                    <button onClick={() => setMessages([])} disabled={messages.length === 0}>
                        清空对话
                    </button>
                </header>

                <section className={styles.archivePanel}>
                    <div className={styles.archiveHeader}>
                        <div>
                            <h3>资料归档</h3>
                            <p>这里显示当前账号通过 RBAC 后实际可见的资料。</p>
                        </div>
                        <button onClick={() => void loadDocuments()} disabled={documentsLoading}>
                            {documentsLoading ? "刷新中..." : "刷新"}
                        </button>
                    </div>
                    {documentsError && <p className={styles.inlineError}>{documentsError}</p>}
                    <div className={styles.archiveGrid}>
                        {documents.map((document) => (
                            <article key={document.doc_id} className={styles.archiveCard}>
                                <strong>{formatDocumentName(document.filename)}</strong>
                                <span>{document.owner_department} · {document.access_level_required}</span>
                                <small>{document.description ?? "课程资料"}</small>
                            </article>
                        ))}
                        {!documentsLoading && documents.length === 0 && (
                            <p className={styles.emptyArchive}>当前身份暂无可见归档资料。</p>
                        )}
                    </div>
                </section>

                <div className={styles.chatLog}>
                    {messages.length === 0 && (
                        <div className={styles.emptyState}>
                            选择左侧推荐问题，或直接输入你想查询的课程资料问题。页面会按当前账号权限显示资料归档和回答范围。
                        </div>
                    )}

                    {messages.map((message, index) => (
                        <article
                            key={`${message.role}-${index}`}
                            className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}
                        >
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                            {message.meta && (
                                <div className={styles.metaStrip}>
                                    <span>{message.meta.blocked ? "已拒绝" : "已回答"}</span>
                                    <span>路由：{message.meta.route || "-"}</span>
                                    <span>来源：{message.meta.sources?.length ?? 0}</span>
                                </div>
                            )}
                        </article>
                    ))}

                    {loading && <p className={styles.loading}>正在检索资料并生成回答...</p>}
                </div>

                <div className={styles.composer}>
                    <textarea
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="输入问题，Enter 发送，Shift+Enter 换行"
                    />
                    <button onClick={() => void submitQuery()} disabled={loading || !input.trim()}>
                        发送
                    </button>
                </div>
            </section>
        </main>
    );
}
