import { useEffect, useRef, useState, useCallback } from "react";
import { getWebSocketUrl } from "@/lib/api";

export interface WSMessagePayload {
  type: "agent_status" | "job_status" | "error" | "progress";
  job_id?: string;
  agent?: string;
  status?: string;
  message?: string;
  progress?: number;
  data?: any;
}

export function useWebSocket(jobId: string | null, onMessageCallback?: (msg: WSMessagePayload) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessagePayload | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    const wsUrl = getWebSocketUrl(jobId);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const payload: WSMessagePayload = JSON.parse(event.data);
        setLastMessage(payload);
        if (onMessageCallback) {
          onMessageCallback(payload);
        }
      } catch (err) {
        console.error("Failed to parse incoming WS message:", err);
      }
    };

    ws.onerror = (err) => {
      console.warn("WebSocket error:", err);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [jobId, onMessageCallback]);

  const sendMessage = useCallback((msg: any) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
}

