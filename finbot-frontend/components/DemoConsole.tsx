"use client";

import { KeyboardEvent, useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import DocumentPanel from "./DocumentPanel";
import { useAuth } from "../context/AuthContext";
import { getRiskDashboard, sendQuery } from "../lib/api";
import { AuthUser, Message, RiskDashboard } from "@/types";
import styles from "./DemoConsole.module.css";

const roleScopes: Record<string, string> = {
    c_level: "可查看全部公司资料与归档",
    engineering: "可查看工程与公共资料",
    finance: "可查看财务与公共资料",
    hr_manager: "可查看 HR 与公共资料",
    marketing: "可查看市场与公共资料",
    employee: "只能查看公共公司资料",
};

const roleViews: Record<string, {
    title: string;
    subtitle: string;
    scope: string[];
    suggestedQuestions: string[];
    helperText: string;
}> = {
    executive: {
        title: "高管资料助手",
        subtitle: "用于总览公司工程、财务、HR、市场和公共资料。",
        scope: ["全部资料库", "工程资料", "财务资料", "HR 资料", "市场资料", "公共资料"],
        suggestedQuestions: [
            "What documents are available in the company archive?",
            "What is the company's total revenue this quarter?",
            "Explain the CI/CD pipeline for the project",
            "What is marketing campaign performance?",
        ],
        helperText: "高管账号可访问全部部门资料，适合演示跨部门检索和审计记录。",
    },
    hr: {
        title: "HR 资料助手",
        subtitle: "用于查询员工数据、招聘计划、入职流程和公共政策。",
        scope: ["HR 资料", "公共资料"],
        suggestedQuestions: [
            "How many employees are in HR?",
            "What is the onboarding process for new employees?",
            "What benefits are offered to employees?",
            "How many types of leave are available?",
        ],
        helperText: "HR 账号只能访问 HR 与公共资料；财务、工程、市场资料会被 RBAC 拦截。",
    },
    finance: {
        title: "财务资料助手",
        subtitle: "用于查询预算、季度报表、费用摘要和公共资料。",
        scope: ["财务资料", "公共资料"],
        suggestedQuestions: [
            "What is the company's total revenue this quarter?",
            "Show me the profit and loss statement",
            "What is the operating budget for 2024?",
            "What are the key financial KPIs?",
        ],
        helperText: "财务账号只能访问 Finance 与公共资料；工程、HR、市场资料会被 RBAC 拦截。",
    },
    engineering: {
        title: "工程资料助手",
        subtitle: "用于查询系统架构、SLA、CI/CD、部署状态和工程指标。",
        scope: ["工程资料", "公共资料"],
        suggestedQuestions: [
            "What is the SLA for our API uptime?",
            "Explain the CI/CD pipeline for the project",
            "How does the microservices setup work?",
            "What are the engineering sprint metrics for 2024?",
        ],
        helperText: "工程账号只能访问 Engineering/R&D 与公共资料；财务、HR、市场资料会被 RBAC 拦截。",
    },
    marketing: {
        title: "市场资料助手",
        subtitle: "用于查询营销活动、获客指标、渠道转化和市场报告。",
        scope: ["市场资料", "公共资料"],
        suggestedQuestions: [
            "What is marketing campaign performance?",
            "How many leads were generated?",
            "What is cost per lead?",
            "Which channels drive conversions?",
        ],
        helperText: "市场账号只能访问 Marketing/Sales 与公共资料；其他部门资料会被 RBAC 拦截。",
    },
    employee: {
        title: "员工公开资料助手",
        subtitle: "用于查询公司公开手册、入职流程、福利和通用政策。",
        scope: ["公开资料"],
        suggestedQuestions: [
            "What is the onboarding process for new employees?",
            "What benefits are offered to employees?",
            "What are the standard work hours?",
            "What is the company leave policy?",
        ],
        helperText: "普通员工只能访问公共资料；部门敏感资料会被 RBAC 拦截。",
    },
};

function getRoleView(user: AuthUser) {
    if (user.is_admin || user.chat_role === "c_level") return roleViews.executive;
    if (user.chat_role === "hr_manager") return roleViews.hr;
    if (user.chat_role === "finance") return roleViews.finance;
    if (user.chat_role === "engineering") return roleViews.engineering;
    if (user.chat_role === "marketing") return roleViews.marketing;
    return roleViews.employee;
}

function formatActionLabel(action: string) {
    return action.replaceAll("_", " ");
}

function formatEventTime(timestamp: string) {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return date.toLocaleString();
}

function DashboardBarRows({ values }: { values: Record<string, number> }) {
    const entries = Object.entries(values).sort((a, b) => b[1] - a[1]);
    const max = Math.max(...entries.map(([, count]) => count), 1);

    if (entries.length === 0) {
        return <p className={styles.emptyArchive}>暂无统计事件。</p>;
    }

    return (
        <>
            {entries.map(([label, count]) => (
                <div className={styles.barRow} key={label}>
                    <span>{formatActionLabel(label)}</span>
                    <div>
                        <i style={{ width: `${Math.max((count / max) * 100, 6)}%` }} />
                    </div>
                    <strong>{count}</strong>
                </div>
            ))}
        </>
    );
}

function AuditDashboard({ token }: { token: string }) {
    const [dashboard, setDashboard] = useState<RiskDashboard | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const loadDashboard = useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            const result = await getRiskDashboard(token, 24);
            setDashboard(result);
        } catch (err) {
            setError(err instanceof Error ? err.message : "无法加载 dashboard");
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        void loadDashboard();
    }, [loadDashboard]);

    const summary = dashboard?.summary;
    const recentEvents = dashboard?.recent_events ?? dashboard?.critical_events ?? [];

    return (
        <div className={styles.workspace}>
            <header className={styles.sectionHeader}>
                <div>
                    <p className={styles.eyebrow}>Audit & Risk Dashboard</p>
                    <h2>安全事件仪表盘</h2>
                </div>
                <button onClick={() => void loadDashboard()} disabled={loading}>
                    {loading ? "刷新中..." : "刷新"}
                </button>
            </header>

            {error && (
                <p className={styles.inlineError}>
                    Dashboard 暂不可用：请确认后端通过根目录 python main.py 或 backend/main.py 启动。
                </p>
            )}

            <div className={styles.metricGrid}>
                <article className={styles.metric}>
                    <span>Total Events</span>
                    <strong>{summary?.total_events ?? 0}</strong>
                </article>
                <article className={styles.metric}>
                    <span>Prompt Attacks</span>
                    <strong>{summary?.attack_count ?? summary?.suspicious_events ?? 0}</strong>
                </article>
                <article className={styles.metric}>
                    <span>Unauthorized</span>
                    <strong>{summary?.unauthorized_access_count ?? summary?.failed_events ?? 0}</strong>
                </article>
                <article className={styles.metric}>
                    <span>Tamper Alerts</span>
                    <strong>{summary?.tamper_detection_count ?? summary?.critical_events ?? 0}</strong>
                </article>
            </div>

            <div className={styles.dashboardColumns}>
                <section>
                    <h3>Events + Alerts</h3>
                    <DashboardBarRows values={dashboard?.by_action ?? {}} />
                </section>
                <section>
                    <h3>Risk Levels</h3>
                    <DashboardBarRows values={dashboard?.by_risk_level ?? {}} />
                </section>
            </div>

            <section className={styles.archivePanel}>
                <div className={styles.archiveHeader}>
                    <div>
                        <h3>Recent Security Events</h3>
                        <p>{dashboard?.period ?? "Last 24 hours"}</p>
                    </div>
                    {dashboard?.generated_at && (
                        <span className={styles.statusBadgeOk}>
                            {formatEventTime(dashboard.generated_at)}
                        </span>
                    )}
                </div>
                <div className={styles.eventList}>
                    {recentEvents.map((event) => (
                        <article key={event.id}>
                            <strong>{formatActionLabel(event.action)}</strong>
                            <span>{event.username ?? "system"}</span>
                            <small>
                                {event.risk_level} · {event.success ? "success" : "blocked"} ·{" "}
                                {formatEventTime(event.timestamp)}
                            </small>
                        </article>
                    ))}
                    {!loading && recentEvents.length === 0 && (
                        <p className={styles.emptyArchive}>暂无最近安全事件。</p>
                    )}
                    {loading && !dashboard && <p className={styles.loading}>正在加载 dashboard...</p>}
                </div>
            </section>
        </div>
    );
}

export default function DemoConsole() {
    const { user, logout } = useAuth();
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [loading, setLoading] = useState(false);
    const [activeView, setActiveView] = useState<"assistant" | "dashboard">("assistant");

    const roleText = useMemo(() => {
        if (!user) return "";
        return `${user.label ?? user.username} / ${user.department} / ${user.level}`;
    }, [user]);
    const roleView = useMemo(() => (user ? getRoleView(user) : roleViews.employee), [user]);

    if (!user) return null;

    const canViewDashboard = user.is_admin || user.chat_role === "c_level";

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

                {canViewDashboard && (
                    <nav className={styles.tabs} aria-label="高管视图">
                        <button
                            type="button"
                            className={activeView === "assistant" ? styles.activeTab : ""}
                            onClick={() => setActiveView("assistant")}
                        >
                            Secure RAG Chat
                        </button>
                        <button
                            type="button"
                            className={activeView === "dashboard" ? styles.activeTab : ""}
                            onClick={() => setActiveView("dashboard")}
                        >
                            Audit & Risk Dashboard
                        </button>
                    </nav>
                )}

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
                {activeView === "dashboard" && canViewDashboard ? (
                    <AuditDashboard token={user.token} />
                ) : (
                    <>
                        <header className={styles.assistantHeader}>
                            <div>
                                <p className={styles.eyebrow}>Secure RAG Chat</p>
                                <h2>{roleView.title}</h2>
                            </div>
                            <button onClick={() => setMessages([])} disabled={messages.length === 0}>
                                清空对话
                            </button>
                        </header>

                        <DocumentPanel user={user} />

                        <div className={styles.chatLog}>
                            {messages.length === 0 && (
                                <div className={styles.emptyState}>
                                    选择左侧推荐问题，或直接输入你想查询的公司资料问题。页面会按当前账号权限显示资料归档和回答范围。
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
                                            {message.meta.sources?.some((s) => s.verified) && (
                                                <span>已验证来源</span>
                                            )}
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
                    </>
                )}
            </section>
        </main>
    );
}
