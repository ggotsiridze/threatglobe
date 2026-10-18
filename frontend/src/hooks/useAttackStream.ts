import { useEffect, useRef, useState } from "react";

import { wsUrl } from "../api/client";
import type { AttackEvent, Hello, ServerMessage, Snapshot, SourceMode } from "../api/types";
import { backoffDelay, type ConnectionState, OFFLINE_AFTER_ATTEMPTS } from "./connection";

export interface StreamHandlers {
  onHello: (hello: Hello) => void;
  onAttack: (event: AttackEvent) => void;
  onSnapshot: (snapshot: Snapshot) => void;
}

const PING_INTERVAL_MS = 20_000;

/**
 * Maintains one WebSocket to /ws/attacks with automatic reconnection.
 * New attacks are pushed by the server; nothing is polled.
 */
export function useAttackStream(handlers: StreamHandlers, url: string = wsUrl()) {
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [mode, setMode] = useState<SourceMode | null>(null);
  const [messages, setMessages] = useState(0);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let pingTimer: ReturnType<typeof setInterval> | undefined;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(url);

      socket.onopen = () => {
        attempt = 0;
        setConnection("open");
        pingTimer = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send("ping"), PING_INTERVAL_MS);
      };

      socket.onmessage = (ev) => {
        let msg: ServerMessage;
        try {
          msg = JSON.parse(ev.data as string) as ServerMessage;
        } catch {
          return; // ignore malformed frames
        }
        setMessages((n) => n + 1);
        if (msg.type === "hello") {
          setMode(msg.data.mode);
          handlersRef.current.onHello(msg.data);
        } else if (msg.type === "attack") {
          handlersRef.current.onAttack(msg.data);
        } else if (msg.type === "snapshot") {
          handlersRef.current.onSnapshot(msg.data);
        }
      };

      socket.onclose = () => {
        clearInterval(pingTimer);
        if (disposed) return;
        attempt += 1;
        setConnection(attempt >= OFFLINE_AFTER_ATTEMPTS ? "offline" : "reconnecting");
        retryTimer = setTimeout(connect, backoffDelay(attempt));
      };

      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      disposed = true;
      clearTimeout(retryTimer);
      clearInterval(pingTimer);
      socket?.close();
    };
  }, [url]);

  return { connection, mode, messages };
}
