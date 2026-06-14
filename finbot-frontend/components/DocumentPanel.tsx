"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
    deleteDocument,
    getAccessibleDocuments,
    getPendingSignatureDocuments,
    getRagIndexStatus,
    signDocument,
    uploadDocument,
} from "../lib/api";
import { AuthUser, DocumentRecord, RagIndexStatus } from "@/types";
import styles from "./DemoConsole.module.css";

const UPLOAD_DEPARTMENTS = [
    { value: "Public", label: "公共资料 (general)" },
    { value: "R&D", label: "工程 (engineering)" },
    { value: "Finance", label: "财务 (finance)" },
    { value: "HR", label: "人力资源 (hr)" },
    { value: "Sales", label: "市场 (marketing)" },
] as const;

function canUploadToDepartment(user: AuthUser, department: string): boolean {
    if (department === "Public") return true;
    if (user.is_admin || user.level === "L1_Executive") return true;
    if (user.level === "L2_Director" || user.level === "L3_Manager") {
        return user.department === department;
    }
    return false;
}

function canSignDocuments(user: AuthUser): boolean {
    return user.is_admin || user.level === "L1_Executive" || user.level === "L2_Director";
}

function canDeleteDocument(user: AuthUser, document: DocumentRecord): boolean {
    if (user.is_admin || user.level === "L1_Executive") return true;
    if (user.level === "L3_Manager") return document.owner_department === user.department;
    return false;
}

function formatDocumentName(filename: string) {
    return filename.replace(/\.(md|csv|txt|pdf|docx)$/i, "").replaceAll("_", " ");
}

function defaultDepartment(user: AuthUser): string {
    if (user.level === "L4_Staff" || user.chat_role === "employee") return "Public";
    if (canUploadToDepartment(user, user.department)) return user.department;
    return "Public";
}

type DocumentPanelProps = {
    user: AuthUser;
};

export default function DocumentPanel({ user }: DocumentPanelProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [documents, setDocuments] = useState<DocumentRecord[]>([]);
    const [pendingDocs, setPendingDocs] = useState<DocumentRecord[]>([]);
    const [ragStatus, setRagStatus] = useState<RagIndexStatus | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [signingId, setSigningId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");

    const [targetDepartment, setTargetDepartment] = useState(defaultDepartment(user));
    const [description, setDescription] = useState("");

    const uploadDepartments = useMemo(
        () => UPLOAD_DEPARTMENTS.filter((item) => canUploadToDepartment(user, item.value)),
        [user],
    );

    const signer = canSignDocuments(user);

    const refreshAll = useCallback(async () => {
        if (!user.token) return;
        setLoading(true);
        setError("");
        try {
            const docs = await getAccessibleDocuments(user.token);
            setDocuments(docs);
            if (signer) {
                const pending = await getPendingSignatureDocuments(user.token);
                setPendingDocs(pending);
                const status = await getRagIndexStatus(user.token);
                setRagStatus(status);
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "无法加载资料");
        } finally {
            setLoading(false);
        }
    }, [signer, user.token]);

    useEffect(() => {
        void refreshAll();
    }, [refreshAll]);

    useEffect(() => {
        if (!signer || !ragStatus?.rebuild_running) return;
        const timer = window.setInterval(() => {
            void getRagIndexStatus(user.token)
                .then(setRagStatus)
                .catch(() => undefined);
        }, 3000);
        return () => window.clearInterval(timer);
    }, [ragStatus?.rebuild_running, signer, user.token]);

    const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const file = fileInputRef.current?.files?.[0];
        if (!file) {
            setError("请选择要上传的文件。");
            return;
        }

        setUploading(true);
        setError("");
        setNotice("");
        try {
            const result = await uploadDocument(user.token, file, {
                targetDepartment,
                accessLevelRequired: user.level,
                description: description.trim() || undefined,
            });
            setNotice(
                result.rag_index_scheduled
                    ? `「${file.name}」已上传、签名并加入知识库重建队列。`
                    : `「${file.name}」已上传并加密，等待高管签名后可被 RAG 检索。`,
            );
            if (fileInputRef.current) fileInputRef.current.value = "";
            setDescription("");
            await refreshAll();
        } catch (err) {
            setError(err instanceof Error ? err.message : "上传失败");
        } finally {
            setUploading(false);
        }
    };

    const handleSign = async (docId: string, filename: string) => {
        setSigningId(docId);
        setError("");
        setNotice("");
        try {
            const result = await signDocument(user.token, docId);
            setNotice(
                result.rag_index_scheduled
                    ? `「${filename}」已签名，知识库正在后台重建，稍后即可提问。`
                    : `「${filename}」已签名。`,
            );
            await refreshAll();
        } catch (err) {
            setError(err instanceof Error ? err.message : "签名失败");
        } finally {
            setSigningId(null);
        }
    };

    const handleDelete = async (docId: string, filename: string) => {
        if (!window.confirm(`确定删除「${formatDocumentName(filename)}」？此操作不可恢复。`)) {
            return;
        }

        setDeletingId(docId);
        setError("");
        setNotice("");
        try {
            const result = await deleteDocument(user.token, docId);
            setNotice(
                result.rag_index_scheduled
                    ? `「${filename}」已删除，知识库正在后台重建。`
                    : `「${filename}」已删除。`,
            );
            await refreshAll();
        } catch (err) {
            setError(err instanceof Error ? err.message : "删除失败");
        } finally {
            setDeletingId(null);
        }
    };

    return (
        <section className={styles.archivePanel}>
            <div className={styles.archiveHeader}>
                <div>
                    <h3>资料归档与安全</h3>
                    <p>
                        上传文件经 AES 加密后存入服务端 <code>documents/</code> 目录（如
                        {" "}
                        <code>doc_xxx.enc</code>
                        ），磁盘上无明文；元数据在 SQLite 数据库。
                    </p>
                </div>
                <button onClick={() => void refreshAll()} disabled={loading}>
                    {loading ? "刷新中..." : "刷新"}
                </button>
            </div>

            {uploadDepartments.length > 0 && (
                <form className={styles.uploadForm} onSubmit={handleUpload}>
                    <h4>上传文档</h4>
                    <div className={styles.uploadGrid}>
                        <label className={styles.uploadField}>
                            <span>文件</span>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".md,.csv,.txt,.docx,.pdf"
                                disabled={uploading}
                            />
                        </label>
                        <label className={styles.uploadField}>
                            <span>目标部门</span>
                            <select
                                value={targetDepartment}
                                onChange={(event) => setTargetDepartment(event.target.value)}
                                disabled={uploading}
                            >
                                {uploadDepartments.map((item) => (
                                    <option key={item.value} value={item.value}>
                                        {item.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className={`${styles.uploadField} ${styles.uploadFieldWide}`}>
                            <span>描述（可选）</span>
                            <input
                                value={description}
                                onChange={(event) => setDescription(event.target.value)}
                                placeholder="例如：Q2 工程 SLA 更新"
                                disabled={uploading}
                            />
                        </label>
                    </div>
                    <button type="submit" className={styles.uploadButton} disabled={uploading}>
                        {uploading ? "上传中..." : "上传并加密"}
                    </button>
                    <small className={styles.uploadHint}>
                        所有角色均可上传到「公共资料 (general)」；部门经理另可上传到本部门。支持 .md / .csv / .txt / .docx。
                    </small>
                </form>
            )}

            {signer && (
                <div className={styles.pendingPanel}>
                    <div className={styles.pendingHeader}>
                        <h4>待高管签名</h4>
                        {ragStatus?.rebuild_running && (
                            <span className={styles.statusBadge}>知识库重建中...</span>
                        )}
                        {ragStatus?.last_result?.status === "ok" && !ragStatus.rebuild_running && (
                            <span className={styles.statusBadgeOk}>
                                已索引 {ragStatus.last_result.chunks} 个片段
                            </span>
                        )}
                    </div>
                    {pendingDocs.length === 0 ? (
                        <p className={styles.emptyArchive}>暂无待签名文档。</p>
                    ) : (
                        <div className={styles.pendingList}>
                            {pendingDocs.map((doc) => (
                                <article key={doc.doc_id} className={styles.pendingCard}>
                                    <div>
                                        <strong>{formatDocumentName(doc.filename)}</strong>
                                        <span>
                                            {doc.owner_department} · {doc.access_level_required}
                                        </span>
                                        <small>{doc.description ?? "等待签名后进入 RAG"}</small>
                                    </div>
                                    <div className={styles.pendingActions}>
                                        <button
                                            type="button"
                                            onClick={() => void handleSign(doc.doc_id, doc.filename)}
                                            disabled={signingId === doc.doc_id || deletingId === doc.doc_id}
                                        >
                                            {signingId === doc.doc_id ? "签名中..." : "签名并入库"}
                                        </button>
                                        {canDeleteDocument(user, doc) && (
                                            <button
                                                type="button"
                                                className={styles.deleteButton}
                                                onClick={() => void handleDelete(doc.doc_id, doc.filename)}
                                                disabled={deletingId === doc.doc_id || signingId === doc.doc_id}
                                            >
                                                {deletingId === doc.doc_id ? "删除中..." : "删除"}
                                            </button>
                                        )}
                                    </div>
                                </article>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {error && <p className={styles.inlineError}>{error}</p>}
            {notice && <p className={styles.inlineNotice}>{notice}</p>}

            <div className={styles.archiveGrid}>
                {documents.map((document) => (
                    <article key={document.doc_id} className={styles.archiveCard}>
                        <strong>{formatDocumentName(document.filename)}</strong>
                        <span>
                            {document.owner_department} · {document.access_level_required}
                        </span>
                        <div className={styles.badgeRow}>
                            {document.is_encrypted && (
                                <span className={styles.badgeSecure}>已加密</span>
                            )}
                            {document.is_signed ? (
                                <span className={styles.badgeSigned}>已签名</span>
                            ) : (
                                <span className={styles.badgePending}>待签名</span>
                            )}
                            {document.is_verified ? (
                                <span className={styles.badgeVerified}>RAG 可用</span>
                            ) : (
                                <span className={styles.badgeMuted}>未入 RAG</span>
                            )}
                        </div>
                        <small>{document.description ?? "公司资料"}</small>
                        {canDeleteDocument(user, document) && (
                            <button
                                type="button"
                                className={styles.deleteButton}
                                onClick={() => void handleDelete(document.doc_id, document.filename)}
                                disabled={deletingId === document.doc_id}
                            >
                                {deletingId === document.doc_id ? "删除中..." : "删除文档"}
                            </button>
                        )}
                    </article>
                ))}
                {!loading && documents.length === 0 && (
                    <p className={styles.emptyArchive}>当前身份暂无可见归档资料。</p>
                )}
            </div>
        </section>
    );
}
