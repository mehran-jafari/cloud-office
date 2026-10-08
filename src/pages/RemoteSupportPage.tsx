import { Copy, Link2, PhoneOff, RefreshCw, ShieldCheck, Monitor } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  addContact,
  connectDeskSignal,
  connectRemote,
  formatDeskId,
  getIceServers,
  getMyDevice,
  listContacts,
  listDeskSessions,
  parseDeskIds,
  patchMyDevice,
  registerDevice,
  sessionAction,
  type DeskContact,
  type DeskDevice,
  type DeskSession,
} from '../api/desk';
import { DeskAgentInstall } from '../components/DeskAgentInstall';

type Incoming = {
  session_key: string;
  from_desk_id: string;
  from_alias?: string;
};

type Tile = {
  sessionKey: string;
  peerId: string;
  peerAlias: string;
  status: string;
  stream?: MediaStream;
};

export function RemoteSupportPage() {
  const [device, setDevice] = useState<DeskDevice | null>(null);
  const [idsInput, setIdsInput] = useState('');
  const [password, setPassword] = useState('');
  const [contacts, setContacts] = useState<DeskContact[]>([]);
  const [history, setHistory] = useState<DeskSession[]>([]);
  const [error, setError] = useState('');
  const [signalState, setSignalState] = useState<'offline' | 'connecting' | 'online'>('offline');
  const [incoming, setIncoming] = useState<Incoming | null>(null);
  const [tiles, setTiles] = useState<Record<string, Tile>>({});
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);

  const signalRef = useRef<ReturnType<typeof connectDeskSignal> | null>(null);
  const pcsRef = useRef<Record<string, RTCPeerConnection>>({});
  const iceRef = useRef<RTCIceServer[]>([{ urls: 'stun:stun.l.google.com:19302' }]);
  const deviceRef = useRef<DeskDevice | null>(null);

  const refreshLists = useCallback(async (token?: string) => {
    try {
      const [c, s] = await Promise.all([listContacts(token), listDeskSessions(token)]);
      setContacts(c);
      setHistory(s);
    } catch { /* */ }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stored = localStorage.getItem('desk_token') || undefined;
        let dev: DeskDevice;
        try {
          dev = await registerDevice({
            token: stored,
            hostname: navigator.platform || 'browser',
            os_name: navigator.userAgent.includes('Mac') ? 'macOS' : navigator.userAgent.includes('Win') ? 'Windows' : 'Web',
            alias: '',
          });
        } catch {
          dev = await getMyDevice(stored);
        }
        if (cancelled) return;
        localStorage.setItem('desk_token', dev.token);
        setDevice(dev);
        deviceRef.current = dev;
        const ice = await getIceServers().catch(() => ({ iceServers: iceRef.current }));
        iceRef.current = ice.iceServers?.length ? ice.iceServers : iceRef.current;
        await refreshLists(dev.token);

        setSignalState('connecting');
        signalRef.current = connectDeskSignal(dev.token, {
          onOpen: () => setSignalState('online'),
          onClose: () => setSignalState('connecting'),
          onMessage: msg => handleSignal(msg),
        });
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'ثبت دستگاه ناموفق');
      }
    })();
    return () => {
      cancelled = true;
      signalRef.current?.close();
      Object.values(pcsRef.current).forEach(pc => pc.close());
      localStream?.getTracks().forEach(t => t.stop());
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSignal(msg: Record<string, unknown>) {
    const type = msg.type as string;
    if (type === 'incoming_session') {
      setIncoming({
        session_key: String(msg.session_key),
        from_desk_id: String(msg.from_desk_id),
        from_alias: msg.from_alias as string | undefined,
      });
      return;
    }
    if (type === 'session_accepted') {
      const key = String(msg.session_key);
      const peer = String(msg.host_desk_id === deviceRef.current?.desk_id ? msg.client_desk_id : msg.host_desk_id);
      void startWebRtc(key, peer, true);
      return;
    }
    if (type === 'session_rejected' || type === 'session_ended') {
      const key = String(msg.session_key);
      endTile(key);
      return;
    }
    if (type === 'offer' || type === 'answer' || type === 'ice') {
      void handleRtcSignal(msg);
    }
  }

  async function ensureLocalScreen(): Promise<MediaStream> {
    if (localStream) return localStream;
    const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    setLocalStream(stream);
    stream.getVideoTracks()[0]?.addEventListener('ended', () => {
      setLocalStream(null);
    });
    return stream;
  }

  async function startWebRtc(sessionKey: string, peerId: string, asOfferer: boolean) {
    if (pcsRef.current[sessionKey]) return;
    const pc = new RTCPeerConnection({ iceServers: iceRef.current });
    pcsRef.current[sessionKey] = pc;

    pc.onicecandidate = ev => {
      if (ev.candidate) {
        signalRef.current?.send({
          type: 'ice',
          to: peerId,
          session_key: sessionKey,
          candidate: ev.candidate,
        });
      }
    };
    pc.ontrack = ev => {
      const stream = ev.streams[0];
      setTiles(prev => ({
        ...prev,
        [sessionKey]: {
          ...(prev[sessionKey] || { sessionKey, peerId, peerAlias: peerId, status: 'active' }),
          stream,
          status: 'active',
        },
      }));
    };

    try {
      const stream = await ensureLocalScreen();
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
    } catch {
      setError('اشتراک صفحه لغو شد یا پشتیبانی نمی‌شود');
    }

    setTiles(prev => ({
      ...prev,
      [sessionKey]: { sessionKey, peerId, peerAlias: peerId, status: 'connecting' },
    }));

    if (asOfferer) {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      signalRef.current?.send({
        type: 'offer',
        to: peerId,
        session_key: sessionKey,
        sdp: offer,
      });
    }
  }

  async function handleRtcSignal(msg: Record<string, unknown>) {
    const sessionKey = String(msg.session_key || '');
    const from = String(msg.from || '');
    if (!sessionKey) return;
    let pc = pcsRef.current[sessionKey];
    if (!pc && msg.type === 'offer') {
      await startWebRtc(sessionKey, from, false);
      pc = pcsRef.current[sessionKey];
    }
    if (!pc) return;

    if (msg.type === 'offer' && msg.sdp) {
      await pc.setRemoteDescription(msg.sdp as RTCSessionDescriptionInit);
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      signalRef.current?.send({ type: 'answer', to: from, session_key: sessionKey, sdp: answer });
    }
    if (msg.type === 'answer' && msg.sdp) {
      await pc.setRemoteDescription(msg.sdp as RTCSessionDescriptionInit);
    }
    if (msg.type === 'ice' && msg.candidate) {
      try {
        await pc.addIceCandidate(msg.candidate as RTCIceCandidateInit);
      } catch { /* */ }
    }
  }

  function endTile(sessionKey: string) {
    pcsRef.current[sessionKey]?.close();
    delete pcsRef.current[sessionKey];
    setTiles(prev => {
      const next = { ...prev };
      delete next[sessionKey];
      return next;
    });
  }

  async function onConnect(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!device) return;
    const ids = parseDeskIds(idsInput);
    if (!ids.length) {
      setError('حداقل یک شناسه ۹ رقمی وارد کنید');
      return;
    }
    for (const id of ids) {
      try {
        const session = await connectRemote(id, password, device.token);
        setTiles(prev => ({
          ...prev,
          [session.session_key]: {
            sessionKey: session.session_key,
            peerId: id,
            peerAlias: id,
            status: session.status,
          },
        }));
        await addContact(id, id, device.token).catch(() => {});
      } catch (err) {
        setError(`${formatDeskId(id)}: ${err instanceof Error ? err.message : 'خطا'}`);
      }
    }
    setIdsInput('');
    refreshLists(device.token);
  }

  async function acceptIncoming() {
    if (!incoming || !device) return;
    try {
      await sessionAction(incoming.session_key, 'accept', device.token);
      await startWebRtc(incoming.session_key, incoming.from_desk_id, false);
      setIncoming(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'پذیرش ناموفق');
    }
  }

  async function rejectIncoming() {
    if (!incoming || !device) return;
    await sessionAction(incoming.session_key, 'reject', device.token).catch(() => {});
    setIncoming(null);
  }

  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">اتصال امن</span>
          <h1>ریموت دسکتاپ</h1>
          <p>شناسه ۹ رقمی مثل AnyDesk — چند اتصال همزمان با WebRTC رمزنگاری‌شده.</p>
        </div>
        <div className="theme-switcher" style={{ gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>
            سیگنال: {signalState === 'online' ? 'آنلاین' : signalState === 'connecting' ? 'در حال اتصال…' : 'آفلاین'}
          </span>
        </div>
      </div>

      <DeskAgentInstall />
      {error && <div className="form-error" role="alert">{error}</div>}

      {incoming && (
        <div className="panel" style={{ marginBottom: 14, borderColor: 'var(--accent)' }}>
          <b>درخواست اتصال ورودی</b>
          <p style={{ margin: '8px 0', color: 'var(--muted)' }}>
            از {incoming.from_alias || formatDeskId(incoming.from_desk_id)} ({formatDeskId(incoming.from_desk_id)})
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="primary" type="button" onClick={acceptIncoming}>پذیرش و اشتراک صفحه</button>
            <button type="button" className="edit-file" onClick={rejectIncoming}>رد</button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: 15 }}>این دستگاه</h2>
          <div style={{
            fontSize: 28, fontWeight: 700, letterSpacing: 2, fontVariantNumeric: 'tabular-nums',
            padding: '12px 0', color: 'var(--accent)',
          }}>
            {formatDeskId(device?.desk_id)}
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <button type="button" className="edit-file" onClick={() => device && navigator.clipboard.writeText(device.desk_id)}>
              <Copy size={14} /> کپی شناسه
            </button>
            <button type="button" className="edit-file" onClick={async () => {
              if (!device) return;
              const d = await patchMyDevice({ rotate_password: true }, device.token);
              setDevice(d);
            }}>
              <RefreshCw size={14} /> تعویض رمز
            </button>
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)', margin: 0 }}>
            رمز اتصال: <b style={{ color: 'var(--text)' }}>{device?.password || '—'}</b>
            {' · '}
            {device?.os_name} · {device?.alias || 'بدون نام'}
          </p>
          <div style={{ marginTop: 12, display: 'flex', gap: 6, alignItems: 'center', fontSize: 12, color: 'var(--muted)' }}>
            <ShieldCheck size={14} color="var(--success)" /> کانال WebRTC · STUN/TURN
          </div>
        </section>

        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: 15 }}>اتصال به سیستم دیگر</h2>
          <form onSubmit={onConnect} style={{ display: 'grid', gap: 10 }}>
            <label>
              شناسه ۹ رقمی (چند شناسه با فاصله)
              <input
                value={idsInput}
                onChange={e => setIdsInput(e.target.value)}
                placeholder="123 456 789"
                inputMode="numeric"
              />
            </label>
            <label>
              رمز اتصال (اگر مقصد رمز دارد)
              <input value={password} onChange={e => setPassword(e.target.value)} type="password" placeholder="اختیاری" />
            </label>
            <button className="primary" type="submit" disabled={!device || signalState !== 'online'}>
              <Link2 size={16} /> اتصال
            </button>
          </form>
        </section>
      </div>

      {Object.keys(tiles).length > 0 && (
        <section style={{ marginTop: 16 }}>
          <h2 style={{ fontSize: 15 }}>اتصالات فعال</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
            {Object.values(tiles).map(tile => (
              <div key={tile.sessionKey} className="panel" style={{ padding: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span><Monitor size={14} /> {formatDeskId(tile.peerId)} · {tile.status}</span>
                  <button type="button" className="edit-file" onClick={async () => {
                    if (device) await sessionAction(tile.sessionKey, 'end', device.token).catch(() => {});
                    endTile(tile.sessionKey);
                  }}>
                    <PhoneOff size={14} /> قطع
                  </button>
                </div>
                {tile.stream ? (
                  <video
                    autoPlay
                    playsInline
                    ref={el => { if (el && tile.stream) el.srcObject = tile.stream; }}
                    style={{ width: '100%', borderRadius: 10, background: '#000', minHeight: 160 }}
                  />
                ) : (
                  <div style={{ padding: 24, textAlign: 'center', color: 'var(--muted)', fontSize: 12 }}>
                    در انتظار تصویر…
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: 14 }}>دفترچه آدرس</h2>
          {contacts.length === 0 ? <p className="muted" style={{ fontSize: 12 }}>هنوز مخاطبی نیست.</p> : (
            contacts.map(c => (
              <div key={c.id} className="file-row" style={{ cursor: 'pointer' }} onClick={() => setIdsInput(c.desk_id)}>
                <div className="file-info">
                  <b>{c.alias || formatDeskId(c.desk_id)}</b>
                  <small>{formatDeskId(c.desk_id)}</small>
                </div>
              </div>
            ))
          )}
        </section>
        <section className="panel">
          <h2 style={{ marginTop: 0, fontSize: 14 }}>تاریخچه نشست‌ها</h2>
          {history.length === 0 ? <p className="muted" style={{ fontSize: 12 }}>نشستی ثبت نشده.</p> : (
            history.slice(0, 12).map(s => (
              <div key={s.session_key} className="file-row">
                <div className="file-info">
                  <b>{formatDeskId(s.host_desk_id)} ↔ {formatDeskId(s.client_desk_id)}</b>
                  <small>{s.status} · {s.started_at ? new Date(s.started_at).toLocaleString('fa-IR') : ''}</small>
                </div>
              </div>
            ))
          )}
        </section>
      </div>
    </>
  );
}
