import {
    AuthUser,
    ChatResponse,
    DocumentRecord,
    RiskDashboard,
    VerifyResult,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const CHAT_TIMEOUT_MS = 120000;

function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatNetworkError(err: unknown) {
    if (err instanceof DOMException && err.name === "AbortError") {
        return "请求超时。首次查询可能仍在构建知识库，请稍等后重试。";
    }

    const detail = err instanceof Error ? err.message : String(err);
    return `无法连接后端服务（${API_URL}）。请确认 backend 正在运行，端口 8000 未被关闭；原始错误：${detail}`;
}

async function parseResponse<T>(res: Response): Promise<T> {
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(payload.detail || `Server error (${res.status})`);
    }
    return payload as T;
}

export async function sendQuery(data: {
    user_id: string;
    role: string;
    query: string;
    session_id?: string;
}): Promise<ChatResponse> {
    let lastError: unknown;

    for (let attempt = 0; attempt < 2; attempt += 1) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS);

        try {
            const res = await fetch(`${API_URL}/api/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "x-session-id": data.user_id,
                },
                body: JSON.stringify({
                    query: data.query,
                    role: data.role,
                    user_id: data.user_id,
                    session_id: data.session_id ?? data.user_id,
                }),
                signal: controller.signal,
            });

            const payload = await res.json().catch(() => ({}));

            if (!res.ok) {
                return {
                    blocked: true,
                    block_reason:
                        payload.detail ||
                        `后端返回错误 (${res.status})，请检查 backend 日志。`,
                };
            }

            return payload;
        } catch (err) {
            lastError = err;
            if (err instanceof DOMException && err.name === "AbortError") {
                break;
            }
            if (attempt === 0) {
                await sleep(700);
            }
        } finally {
            clearTimeout(timeout);
        }
    }

    return {
        blocked: true,
        block_reason: formatNetworkError(lastError),
    };
}

export async function loginDemoUser(username: string, password: string, chatRole: AuthUser["chat_role"], label?: string) {
    const res = await fetch(`${API_URL}/api/auth/login/json`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });
    const tokenPayload = await parseResponse<{ access_token: string; token_type: string }>(res);

    const meRes = await fetch(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${tokenPayload.access_token}` },
        cache: "no-store",
    });
    const profile = await parseResponse<Omit<AuthUser, "token" | "chat_role">>(meRes);

    return {
        ...profile,
        token: tokenPayload.access_token,
        chat_role: chatRole,
        label,
    } as AuthUser;
}

export async function seedDemoData() {
    const res = await fetch(`${API_URL}/api/demo/seed`, { method: "POST" });
    return parseResponse<{ message: string; documents: DocumentRecord[] }>(res);
}

export async function getDemoDocuments() {
    const res = await fetch(`${API_URL}/api/demo/documents`, { cache: "no-store" });
    return parseResponse<{ documents: DocumentRecord[] }>(res);
}

export async function getAccessibleDocuments(token: string) {
    const res = await fetch(`${API_URL}/api/documents/`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
    });
    return parseResponse<DocumentRecord[]>(res);
}

export async function verifyDocument(docId: string, token: string) {
    const res = await fetch(`${API_URL}/api/documents/${docId}/verify`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
    });
    return parseResponse<VerifyResult>(res);
}

export async function simulateTamper() {
    const res = await fetch(`${API_URL}/api/demo/tamper-simulation`, { method: "POST" });
    return parseResponse<{ blocked: boolean; status: string; message: string; document?: DocumentRecord }>(res);
}

export async function getRiskDashboard(hours = 24) {
    const res = await fetch(`${API_URL}/api/demo/risk-dashboard?hours=${hours}`, {
        cache: "no-store",
    });
    return parseResponse<RiskDashboard>(res);
}

export async function getHealth() {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return parseResponse<{ status: string; boot_id: string; services: Record<string, string> }>(res);
}
