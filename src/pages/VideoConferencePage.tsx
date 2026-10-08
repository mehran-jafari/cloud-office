import {
  ArrowRight,
  Camera,
  CameraOff,
  CheckCircle2,
  CircleAlert,
  LockKeyhole,
  MessageCircle,
  Mic,
  MicOff,
  MonitorUp,
  PhoneOff,
  ScreenShare,
  Send,
  ShieldCheck,
  Video,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthProvider';
import { endRemoteSession, getRemoteSession } from '../api/remote';
import { useRemoteConference } from '../hooks/useRemoteConference';
import type { RemoteSession } from '../types/api';
import { conferenceDoc, meetingSummary, speechToText, type ConferenceDocKind } from '../api/ai';
import { createConference, formatDeskId, getMyDevice, parseDeskIds } from '../api/desk';

const channelStatus: Record<'offline' | 'connecting' | 'connected' | 'failed', string> = {
  offline: 'خارج از کانال',
  connecting: 'در حال اتصال امن',
  connected: 'کانال رمزنگاری‌شده فعال',
  failed: 'اختلال در کانال',
};

export function VideoConferencePage() {
  const [meetingNotes, setMeetingNotes] = useState('');
  const [meetingOut, setMeetingOut] = useState('');
  const [confCode, setConfCode] = useState('');
  const [inviteIds, setInviteIds] = useState('');
  const { user, accessToken } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [session, setSession] = useState<RemoteSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [chatBody, setChatBody] = useState('');
  const localVideo = useRef<HTMLVideoElement>(null);
  const remoteVideo = useRef<HTMLVideoElement>(null);
  const sessionId = Number(searchParams.get('session'));
  const conference = useRemoteConference(session?.status === 'active' ? session : null, accessToken, user?.id ?? null);

  useEffect(() => {
    if (!Number.isInteger(sessionId) || sessionId <= 0) {
      setLoading(false);
      return;
    }
    setLoading(true);
    getRemoteSession(sessionId)
      .then(setSession)
      .catch(reason => { setSession(null); setError(reason instanceof Error ? reason.message : 'جلسه موردنظر پیدا نشد.'); })
      .finally(() => setLoading(false));
  }, [sessionId]);

  useEffect(() => { if (localVideo.current) localVideo.current.srcObject = conference.localStream; }, [conference.localStream]);
  useEffect(() => { if (remoteVideo.current) remoteVideo.current.srcObject = conference.remoteStream; }, [conference.remoteStream]);

  async function startCamera() {
    try {
      if (conference.mediaMode === 'camera') conference.stopLocalMedia();
      else await conference.startCamera();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'دسترسی به دوربین و میکروفون رد شد.');
    }
  }

  async function startScreenShare() {
    try {
      if (conference.mediaMode === 'screen') conference.stopLocalMedia();
      else await conference.startScreenShare();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'دسترسی به صفحه نمایش رد شد.');
    }
  }

  async function endSession() {
    if (!session) return;
    setError('');
    try {
      conference.stop();
      const updated = await endRemoteSession(session.id);
      setSession(updated);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'پایان دادن به جلسه ناموفق بود.');
    }
  }

  function sendChat() {
    const value = chatBody.trim();
    if (!value) return;
    if (!conference.sendChat(value)) { setError('کانال چت هنوز آماده نیست؛ چند لحظه بعد دوباره تلاش کنید.'); return; }
    setError(''); setChatBody('');
  }

  if (loading) return <div className="conference-empty-state"><Video size={28} /><h2>در حال آماده‌سازی اتاق امن…</h2></div>;

  if (!session || session.status !== 'active') {
    return <div className="conference-empty-state"><LockKeyhole size={30} /><h2>اتاق کنفرانس هنوز فعال نیست</h2><p>برای ورود، ابتدا باید اتصال امن توسط صاحب سیستم تأیید شود.</p><button className="primary" onClick={() => navigate('/remote-support')}>بازگشت به اتصال امن</button>{error && <small>{error}</small>}</div>;
  }

  const localLabel = conference.mediaMode === 'screen' ? 'اشتراک صفحه شما' : conference.mediaMode === 'camera' ? 'دوربین شما' : 'رسانه محلی خاموش است';
  const remoteLabel = session.agent === user?.id ? session.requester_name : session.agent_name ?? 'طرف مقابل';

  return (
    <div className="conference-studio">
      <header className="conference-studio__head">
        <div><button className="back-link" onClick={() => navigate(`/remote-support?session=${session.id}`)}><ArrowRight size={16} />بازگشت به اتصال امن</button><h1>استودیوی ویدیو کنفرانس</h1><p>تصویر، صدا و چت فقط برای اعضای تأییدشده این جلسه در دسترس است.</p></div>
        <div className={`channel-pill channel-${conference.status}`}><i />{channelStatus[conference.status]}</div>
      </header>

      {error && <div className="secure-alert" role="alert"><CircleAlert size={17} />{error}</div>}

      <div className="conference-layout">
        <section className="conference-stage">
          <div className="conference-stage__topline"><span><ShieldCheck size={15} />جلسه #{session.id}</span><span>{session.requester_name} <b>و</b> {session.agent_name ?? 'کارشناس'}</span></div>
          <div className="remote-stage">
            {conference.remoteStream ? <video className="remote-stage__video" ref={remoteVideo} autoPlay playsInline /> : <div className="remote-stage__placeholder"><div className="video-avatar">{remoteLabel.slice(0, 1)}</div><b>{remoteLabel}</b><span>در انتظار جریان ویدیو یا اشتراک صفحه</span></div>}
            <div className="remote-stage__label"><span className="live-dot" />{remoteLabel}</div>
            <div className="local-pip">{conference.localStream ? <video ref={localVideo} autoPlay muted playsInline /> : <div><CameraOff size={20} /><small>رسانه شما خاموش است</small></div>}<span>{localLabel}</span></div>
          </div>
          <div className="media-dock" aria-label="کنترل‌های رسانه"><button className={`media-control ${conference.mediaMode === 'screen' ? 'is-active' : ''}`} onClick={() => void startScreenShare()}><ScreenShare size={20} /><span>{conference.mediaMode === 'screen' ? 'توقف اشتراک' : 'اشتراک صفحه'}</span></button><button className={`media-control ${conference.mediaMode === 'camera' ? 'is-active' : ''}`} onClick={() => void startCamera()}>{conference.mediaMode === 'camera' ? <CameraOff size={20} /> : <Camera size={20} />}<span>{conference.mediaMode === 'camera' ? 'خاموش‌کردن دوربین' : 'دوربین و صدا'}</span></button><button className={`media-control ${conference.microphoneMuted ? 'is-muted' : ''}`} onClick={conference.toggleMic} disabled={!conference.localStream}>{conference.microphoneMuted ? <MicOff size={20} /> : <Mic size={20} />}<span>{conference.microphoneMuted ? 'بی‌صدا' : 'میکروفون'}</span></button><button className="media-control media-control--end" onClick={() => void endSession()}><PhoneOff size={20} /><span>پایان جلسه</span></button></div>
        </section>

        <aside className="conference-sidepanel">
          <section className="conference-status-card"><div className="conference-status-card__icon"><LockKeyhole size={19} /></div><div><span>امنیت جلسه</span><b>رضایت ثبت شده</b><small>اتصال فقط بین دو عضو مجاز برقرار است.</small></div><CheckCircle2 size={20} /></section>
          <section className="participant-card"><div className="participant-card__head"><span>شرکت‌کنندگان</span><b>۲ نفر</b></div><div className="participant"><span>{session.requester_name.slice(0, 1)}</span><div><b>{session.requester_name}</b><small>صاحب سیستم</small></div><i className="participant-status" /></div><div className="participant"><span>{(session.agent_name ?? 'ک').slice(0, 1)}</span><div><b>{session.agent_name ?? 'کارشناس'}</b><small>کارشناس مجاز</small></div><i className="participant-status" /></div></section>
          <section className="conference-chat-panel"><div className="conference-chat-panel__head"><div><MessageCircle size={18} /><b>چت جلسه</b></div><span className={conference.status === 'connected' ? 'chat-ready' : 'chat-waiting'}>{conference.status === 'connected' ? 'آماده ارسال' : 'در انتظار اتصال'}</span></div><div className="conference-message-list">{conference.messages.length ? conference.messages.map(message => <article className={`conference-message ${message.is_staff_reply ? 'is-agent' : ''} ${String(message.id).startsWith('local-') ? 'is-pending' : ''}`} key={`${message.id}-${message.client_id ?? ''}`}><small>{message.sender_name}{String(message.id).startsWith('local-') ? ' · در حال ارسال' : ''}</small><p>{message.body}</p></article>) : <div className="conference-chat-empty"><MessageCircle size={22} /><span>گفتگو در این جلسه هنوز آغاز نشده است.</span></div>}</div><div className="conference-compose"><textarea value={chatBody} onChange={event => setChatBody(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendChat(); } }} rows={2} placeholder={conference.status === 'connected' ? 'پیام داخل جلسه…' : 'با اتصال کانال، ارسال چت فعال می‌شود…'} /><button className="primary" onClick={sendChat} disabled={!chatBody.trim() || conference.status !== 'connected'} aria-label="ارسال پیام"><Send size={17} /></button></div></section>
        </aside>
      </div>
    
      <section className="panel conference-ai-panel" style={{ marginTop: 16 }}>
        <h2 style={{ fontSize: 14, marginTop: 0 }}>رونوشت و خروجی جلسه</h2>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 0 }}>
          صوت/ویدیوی جلسه را آپلود کنید تا متن کامل استخراج شود؛ سپس صورت‌جلسه یا سایر خروجی‌ها را بسازید.
        </p>
        <textarea
          value={meetingNotes}
          onChange={e => setMeetingNotes(e.target.value)}
          rows={8}
          placeholder="متن کامل صحبت‌های جلسه اینجا می‌آید…"
          style={{ width: '100%', padding: 10, borderRadius: 10, background: 'var(--fill-quaternary)', border: '1px solid var(--line)', color: 'var(--text)' }}
        />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8, alignItems: 'center' }}>
          <label className="edit-file" style={{ cursor: 'pointer' }}>
            استخراج متن از صوت/ویدیو
            <input
              type="file"
              accept="audio/*,video/*"
              style={{ display: 'none' }}
              onChange={async e => {
                const f = e.target.files?.[0];
                if (!f) return;
                try {
                  const res = await speechToText(f, f.name);
                  const text = res.text || '';
                  setMeetingNotes(prev => {
                    const base = prev.trim();
                    return base ? base + '\n\n' + text : text;
                  });
                  if (res.usable === false) alert(text);
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'خطا در تبدیل گفتار');
                } finally {
                  e.target.value = '';
                }
              }}
            />
          </label>
          <button
            className="edit-file"
            type="button"
            disabled={!meetingNotes.trim()}
            onClick={async () => {
              try {
                const res = await conferenceDoc(meetingNotes, 'transcript_clean', 'ویدیوکنفرانس');
                setMeetingNotes(res.text || meetingNotes);
              } catch (err) {
                alert(err instanceof Error ? err.message : 'خطا');
              }
            }}
          >
            مرتب‌سازی رونوشت
          </button>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
          {([
            ['minutes', 'صورت‌جلسه'],
            ['actions', 'اقدامات و پیگیری'],
            ['executive', 'خلاصه اجرایی'],
            ['email', 'ایمیل به شرکت‌کنندگان'],
            ['summary', 'خلاصه کلی'],
          ] as const).map(([kind, label]) => (
            <button
              key={kind}
              type="button"
              className="primary small-button"
              disabled={!meetingNotes.trim() || meetingNotes.trim().length < 15}
              onClick={async () => {
                try {
                  if (kind === 'summary') {
                    const res = await meetingSummary(meetingNotes, 'ویدیوکنفرانس');
                    setMeetingOut(res.text || '');
                  } else {
                    const res = await conferenceDoc(meetingNotes, kind as ConferenceDocKind, 'ویدیوکنفرانس');
                    setMeetingOut(res.text || '');
                  }
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'خطا');
                }
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {meetingOut ? (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
              <b style={{ fontSize: 12 }}>خروجی</b>
              <button
                type="button"
                className="edit-file"
                onClick={() => navigator.clipboard.writeText(meetingOut)}
              >
                کپی
              </button>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, margin: 0, padding: 12, borderRadius: 12, background: 'var(--fill-quaternary)', border: '1px solid var(--line)' }}>{meetingOut}</pre>
          </div>
        ) : null}
      </section>
</div>
  );
}
