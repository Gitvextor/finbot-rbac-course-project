"use client";
import { useState } from "react";
import LoginModal from "../components/loginModal";
import ChatBot from "../components/ChatBox";
import { useAuth } from "../context/AuthContext";

export default function Home() {
  const { user, authReady } = useAuth();
  const [showModal, setShowModal] = useState(false);

  if (!authReady) {
    return (
      <div className="landing">
        <h1>FinBot 💼</h1>
        <p>正在连接服务…</p>
      </div>
    );
  }

  return (
    <div>
      {!user ? (
        <div className="landing">
          <h1>FinBot 💼</h1>
          <button onClick={() => setShowModal(true)}>登录</button>

          {showModal && <LoginModal onClose={() => setShowModal(false)} />}
        </div>
      ) : (
        <ChatBot />
      )}
    </div>
  );
}
