"use client";
import { createContext, useContext, useState, useEffect } from "react";
import { AuthUser } from "@/types";

type User = AuthUser | null;

type AuthContextType = {
    user: User;
    authReady: boolean;
    login: (user: AuthUser) => void;
    legacyLogin: (user_id: string, role: string) => void;
    logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const USER_KEY = "finbot_user";
const BOOT_KEY = "finbot_server_boot_id";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    const [user, setUser] = useState<User>(null);
    const [authReady, setAuthReady] = useState(false);

    useEffect(() => {
        const syncAuthWithServer = async () => {
            try {
                const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
                if (!res.ok) throw new Error("health check failed");

                const data = await res.json();
                const bootId = data.boot_id as string | undefined;
                const storedBootId = localStorage.getItem(BOOT_KEY);

                if (!bootId || bootId !== storedBootId) {
                    localStorage.removeItem(USER_KEY);
                    if (bootId) {
                        localStorage.setItem(BOOT_KEY, bootId);
                    }
                    setUser(null);
                    return;
                }

                const stored = localStorage.getItem(USER_KEY);
                if (stored) {
                    setUser(JSON.parse(stored));
                }
            } catch {
                localStorage.removeItem(USER_KEY);
                setUser(null);
            } finally {
                setAuthReady(true);
            }
        };

        void syncAuthWithServer();
    }, []);

    const login = (userData: AuthUser) => {
        setUser(userData);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));
    };

    const legacyLogin = (user_id: string, role: string) => {
        const userData = {
            id: 0,
            username: user_id,
            email: `${user_id}@local.demo`,
            level: "Demo",
            department: "Demo",
            is_admin: role === "c_level",
            chat_role: role,
            token: "",
            label: role,
        } as AuthUser;
        login(userData);
    };

    const logout = () => {
        setUser(null);
        localStorage.removeItem(USER_KEY);
    };

    return (
        <AuthContext.Provider value={{ user, authReady, login, legacyLogin, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error("useAuth must be used within AuthProvider");
    return context;
};
