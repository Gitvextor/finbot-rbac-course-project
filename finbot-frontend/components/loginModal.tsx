"use client";

import { FormEvent, useMemo, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { DEMO_ACCOUNTS } from "../lib/memberCredentials";
import { loginDemoUser, seedDemoData } from "../lib/api";
import styles from "./LoginModal.module.css";

type DemoAccount = (typeof DEMO_ACCOUNTS)[number];

export default function LoginModal({ onClose }: { onClose: () => void }) {
    const [selectedKey, setSelectedKey] = useState<DemoAccount["key"]>("employee");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const { login } = useAuth();

    const selectedAccount = useMemo(
        () => DEMO_ACCOUNTS.find((account) => account.key === selectedKey) ?? DEMO_ACCOUNTS[0],
        [selectedKey],
    );

    const fillDemoAccount = () => {
        setUsername(selectedAccount.username);
        setPassword("");
        setError("");
    };

    const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!username.trim() || !password.trim()) {
            setError("请输入账号和密码。");
            return;
        }

        setLoading(true);
        setError("");

        try {
            try {
                await seedDemoData();
            } catch (seedErr) {
                console.warn("Demo seed skipped:", seedErr);
            }

            const user = await loginDemoUser(
                username.trim(),
                password,
                selectedAccount.chat_role,
                selectedAccount.label,
            );

            if (user.username !== selectedAccount.username) {
                setError(`账号 ${user.username} 不属于 ${selectedAccount.label}，已拒绝登录。`);
                return;
            }

            if (
                user.level !== selectedAccount.level ||
                user.department !== selectedAccount.department ||
                user.is_admin !== selectedAccount.is_admin
            ) {
                setError("账号权限与所选身份不匹配，已拒绝登录。");
                return;
            }

            login(user);
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : "登录失败，请检查后端服务和账号密码。");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.modalOverlay}>
            <form className={styles.modal} onSubmit={handleLogin}>
                <h2>登录 FinBot</h2>
                <p className={styles.subtitle}>先选择身份，再用对应账号密码登录；身份不匹配会被拒绝。</p>

                <div className={styles.demoGrid} role="list" aria-label="选择登录身份">
                    {DEMO_ACCOUNTS.map((account) => (
                        <button
                            key={account.key}
                            type="button"
                            className={`${styles.demoButton} ${
                                selectedKey === account.key ? styles.selectedDemoButton : ""
                            }`}
                            onClick={() => {
                                setSelectedKey(account.key);
                                setUsername("");
                                setPassword("");
                                setError("");
                            }}
                            disabled={loading}
                        >
                            <strong>{account.label}</strong>
                            <span>{account.scenario}</span>
                        </button>
                    ))}
                </div>

                <div className={styles.selectedPanel}>
                    <div>
                        <span>已选择身份</span>
                        <strong>{selectedAccount.label}</strong>
                        <small>演示账号：{selectedAccount.username}</small>
                    </div>
                    <button type="button" onClick={fillDemoAccount} disabled={loading}>
                        填入演示账号
                    </button>
                </div>

                <label className={styles.field}>
                    <span>账号</span>
                    <input
                        value={username}
                        onChange={(event) => setUsername(event.target.value)}
                        placeholder="例如 finance_manager"
                        autoComplete="username"
                    />
                </label>

                <label className={styles.field}>
                    <span>密码</span>
                    <input
                        type="password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        placeholder="请输入密码"
                        autoComplete="current-password"
                    />
                </label>

                {error && <p className={styles.error}>{error}</p>}

                <button className={styles.primary} type="submit" disabled={loading}>
                    {loading ? "登录中..." : "登录"}
                </button>
                <button className={styles.secondary} type="button" onClick={onClose}>
                    取消
                </button>
            </form>
        </div>
    );
}
