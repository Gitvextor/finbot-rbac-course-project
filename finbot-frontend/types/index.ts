export interface Message {
    role: "user" | "assistant";
    content: string;
    meta?: ChatResponse;
}

export type ChatRole =
    | "employee"
    | "hr_manager"
    | "finance"
    | "marketing"
    | "engineering"
    | "c_level";

export interface DemoAccount {
    key: "admin" | "teacher" | "ta" | "student";
    label: string;
    username: string;
    email: string;
    password: string;
    level: string;
    department: string;
    is_admin: boolean;
    chat_role: ChatRole;
    scenario: string;
}

export interface AuthUser {
    id: number;
    username: string;
    email: string;
    level: string;
    department: string;
    is_admin: boolean;
    chat_role: ChatRole;
    token: string;
    label?: string;
}

export interface ChatResponse {
    role?: string;
    route?: string;
    allowed_collections?: string[];
    blocked?: boolean;
    guardrail_triggered?: boolean;
    block_reason?: string;
    answer?: string | null;
    sources?: { source: string; verified?: boolean }[];
    detail?: string;
}

export interface DocumentRecord {
    id?: number;
    doc_id: string;
    filename: string;
    file_size: number;
    file_type: string;
    is_encrypted: boolean;
    sha256_hash: string;
    is_signed: boolean;
    owner_department: string;
    access_level_required: string;
    is_verified: boolean;
    created_at?: string;
    description?: string;
}

export interface VerifyResult {
    doc_id: string;
    filename: string;
    stored_hash: string;
    current_hash?: string;
    is_signed: boolean;
    is_verified: boolean;
    signature_valid?: boolean | null;
    integrity_check: string;
    status: string;
    error?: string;
}

export interface RiskDashboard {
    period: string;
    generated_at: string;
    summary: {
        attack_count: number;
        sensitive_query_count: number;
        unauthorized_access_count: number;
        tamper_detection_count: number;
        total_events: number;
    };
    by_action: Record<string, number>;
    by_risk_level: Record<string, number>;
    recent_events: AuditEvent[];
}

export interface AuditEvent {
    id: number;
    user_id?: number | null;
    username?: string | null;
    action: string;
    resource_type?: string | null;
    resource_id?: string | null;
    details?: string | null;
    risk_level: string;
    is_suspicious: boolean;
    success: boolean;
    error_message?: string | null;
    timestamp: string;
}
