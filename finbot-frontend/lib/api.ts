export async function sendQuery(data: {
    user_id: string;
    role: string;
    query: string;
}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000);

    try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-session-id": data.user_id,
            },
            body: JSON.stringify(data),
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