"use client";
import { useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import {
    MEMBER_OPTIONS,
    MemberRole,
    getMemberHint,
    verifyMemberPassword,
} from "../lib/memberCredentials";
import styles from "./LoginModal.module.css";

export default function LoginModal({ onClose }: { onClose: () => void }) {
    const [userId, setUserId] = useState("");
    const [password, setPassword] = useState("");
    const [role, setRole] = useState<MemberRole>("employee");
    const [error, setError] = useState("");
    const { login } = useAuth();

    const roleHint = useMemo(() => getMemberHint(role), [role]);

    const handleLogin = () => {
        if (!userId.trim()) {
            setError("请输入用户 ID");
            return;
        }
        if (!password) {
            setError("请输入该成员类型的专属密码");
            return;
        }
        if (!verifyMemberPassword(role, password)) {
            setError("密码错误，请确认成员类型与密码匹配");
            return;
        }

        login(userId.trim(), role);
        onClose();
    };

    return (
        <div className={styles.modalOverlay}>
            <div className={styles.modal}>
                <h2>登录 FinBot</h2>
                <p className={styles.subtitle}>每种成员类型使用独立密码</p>

                <label className={styles.label}>用户 ID</label>
                <input
                    placeholder="例如：user001"
                    value={userId}
                    onChange={(e) => {
                        setUserId(e.target.value);
                        setError("");
                    }}
                />

                <label className={styles.label}>成员类型</label>
                <select
                    value={role}
                    onChange={(e) => {
                        setRole(e.target.value as MemberRole);
                        setPassword("");
                        setError("");
                    }}
                >
                    {MEMBER_OPTIONS.map((member) => (
                        <option key={member.role} value={member.role}>
                            {member.label}
                        </option>
                    ))}
                </select>

                <p className={styles.hint}>{roleHint}</p>

                <label className={styles.label}>专属密码</label>
                <input
                    type="password"
                    placeholder="请输入该成员类型的密码"
                    value={password}
                    onChange={(e) => {
                        setPassword(e.target.value);
                        setError("");
                    }}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") handleLogin();
                    }}
                />

                {error && <p className={styles.error}>{error}</p>}

                <button className={styles.primary} onClick={handleLogin}>
                    登录
                </button>
                <button className={styles.secondary} onClick={onClose}>
                    取消
                </button>
            </div>
        </div>
    );
}
