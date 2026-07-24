import { useEffect, useRef, useCallback, useState } from 'react';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

interface WsEvent {
  type: string;
  task_id: string;
  step_id?: string;
  event_id?: string;
  step?: Record<string, unknown>;
  status?: string;
  email_draft?: Record<string, unknown>;
  [key: string]: unknown;
}

interface UseWebSocketOptions {
  taskId: string | null;
  onEvent: (event: WsEvent) => void;
  onStatusChange?: (status: ConnectionStatus) => void;
}

export function useWebSocket({ taskId, onEvent, onStatusChange }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const reconnectCount = useRef(0);
  const seenEvents = useRef<Set<string>>(new Set());
  const mountedRef = useRef(true);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  const setConnStatus = useCallback((s: ConnectionStatus) => {
    setStatus(s);
    onStatusChange?.(s);
  }, [onStatusChange]);

  const connect = useCallback(() => {
    if (!taskId) return;
    if (!mountedRef.current) return;

    const WS_BASE = import.meta.env.VITE_WS_BASE ?? 'ws://localhost:8000/ws';
    const url = `${WS_BASE}/tasks/${taskId}`;

    setConnStatus('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectCount.current = 0;
      setConnStatus('connected');
    };

    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data);
        if (event.type === 'heartbeat') return;

        // 去重：按 event_id
        const eid = event.event_id;
        if (eid) {
          if (seenEvents.current.has(eid)) return;
          seenEvents.current.add(eid);
          if (seenEvents.current.size > 500) {
            const arr = [...seenEvents.current];
            seenEvents.current = new Set(arr.slice(-250));
          }
        }

        onEventRef.current(event);
      } catch { /* ignore */ }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!mountedRef.current) return;
      setConnStatus('disconnected');
      const delay = Math.min(1000 * Math.pow(2, reconnectCount.current), 15000);
      reconnectCount.current += 1;
      reconnectTimer.current = setTimeout(connect, delay);
    };

    ws.onerror = () => { ws.close(); };
  }, [taskId, setConnStatus]);

  const disconnect = useCallback(() => {
    mountedRef.current = false;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    wsRef.current?.close();
    wsRef.current = null;
    setConnStatus('disconnected');
  }, [setConnStatus]);

  useEffect(() => {
    mountedRef.current = true;
    seenEvents.current = new Set();
    reconnectCount.current = 0;
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { status, reconnect: connect, disconnect };
}
