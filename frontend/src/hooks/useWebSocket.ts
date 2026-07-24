import { useEffect, useRef, useCallback, useState } from 'react';
import type { WsEvent } from '@/types';

const WS_BASE = import.meta.env.VITE_WS_BASE ?? 'ws://localhost:8000/ws';

interface UseWebSocketOptions {
  taskId: string | null;
  onEvent: (event: WsEvent) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

export function useWebSocket({ taskId, onEvent, onConnected, onDisconnected }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!taskId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}/tasks/${taskId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      onConnected?.();
    };

    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data);
        onEventRef.current(event);
      } catch {
        // 忽略解析失败的消息
      }
    };

    ws.onclose = () => {
      setConnected(false);
      onDisconnected?.();
      // 自动重连
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [taskId, onConnected, onDisconnected]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connected, reconnect: connect, disconnect };
}
