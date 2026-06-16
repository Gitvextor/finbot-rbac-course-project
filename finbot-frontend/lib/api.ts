import {
    AuthUser,
    ChatResponse,
    DocumentRecord,
    RagIndexStatus,
    RiskDashboard,
    SignDocumentResponse,
    UploadDocumentResponse,
    VerifyResult,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

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
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

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
                    `Server error (${res.status}). Check backend logs.`,
            };
        }

        return payload;
    } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
            return {
                blocked: true,
                block_reason:
                    "Request timed out. First query may still be building the knowledge base; wait and retry.",
            };
        }

        return {
            blocked: true,
            block_reason: "Failed to connect to server",
        };
    } finally {
        clearTimeout(timeout);
    }
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

export async function uploadDocument(
    token: string,
    file: File,
    options: {
        targetDepartment: string;
        accessLevelRequired?: string;
        description?: string;
        signDocument?: boolean;
    },
): Promise<UploadDocumentResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_department", options.targetDepartment);
    formData.append("access_level_required", options.accessLevelRequired ?? "L4_Staff");
    if (options.description) {
        formData.append("description", options.description);
    }
    formData.append("sign_document", String(options.signDocument ?? true));

    const res = await fetch(`${API_URL}/api/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
    });
    return parseResponse<UploadDocumentResponse>(res);
}

export async function getPendingSignatureDocuments(token: string) {
    const res = await fetch(`${API_URL}/api/documents/pending-signature`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
    });
    return parseResponse<DocumentRecord[]>(res);
}

export async function signDocument(token: string, docId: string, force = false) {
    const res = await fetch(
        `${API_URL}/api/documents/${docId}/sign?force=${force ? "true" : "false"}`,
        {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        },
    );
    return parseResponse<SignDocumentResponse>(res);
}

export async function getRagIndexStatus(token: string) {
    const res = await fetch(`${API_URL}/api/rag/status`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
    });
    return parseResponse<RagIndexStatus>(res);
}

export async function reindexRag(token: string, background = true) {
    const res = await fetch(`${API_URL}/api/rag/reindex?background=${background}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
    });
    return parseResponse<RagIndexStatus & { message: string }>(res);
}

export async function deleteDocument(token: string, docId: string) {
    const res = await fetch(`${API_URL}/api/documents/${docId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
    return parseResponse<{ message: string; success: boolean; rag_index_scheduled?: boolean }>(res);
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

export async function getRiskDashboard(token: string, hours = 24) {
    const res = await fetch(`${API_URL}/api/audit/dashboard?hours=${hours}`, {
        headers: { Authorization: `Bearer ${token}` },
        cache: "no-store",
    });
    return parseResponse<RiskDashboard>(res);
}

export async function getHealth() {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return parseResponse<{ status: string; boot_id: string; services: Record<string, string> }>(res);
}
