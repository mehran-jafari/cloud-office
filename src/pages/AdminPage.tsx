import { BadgeCheck, Check, ChevronLeft, HardDrive, KeyRound, Plus, ShieldCheck, SlidersHorizontal, UserCog, UserPlus, UsersRound, X, Activity, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { createAdminUser, createRoleDefinition, listAdminUsers, listRoleDefinitions, listSupportAgents, setSupportReplyPermission, updateAdminUser, updateRoleDefinition, updateUserQuota, updateUserRole, type AdminUser, type RoleDefinition } from '../api/admin';
import { useAuth } from '../auth/AuthProvider';
import type { SupportAgentPermission, SupportAgentPerformance } from '../types/api';
import { fetchSupportPerformance, runSupportEscalations } from '../api/support';

const roleLabels: Record<string, string> = { owner: 'مالک سازمان', admin: 'مدیر سیستم', support: 'کارشناس پشتیبانی', auditor: 'حسابرس', member: 'کاربر فضای کاری' };
const permissionGroups = [
  { title: 'فرماندهی سازمان', hint: 'هویت‌ها و نمای مدیریتی', items: [['manage_users', 'مدیریت کاربران'], ['view_admin', 'دسترسی به پنل مدیریت']] },
  { title: 'فضای همکاری', hint: 'فایل، مکاتبات و گزارش‌ها', items: [['view_files', 'مشاهده فایل‌ها'], ['edit_files', 'ویرایش فایل‌ها'], ['view_mail', 'مشاهده مکاتبات'], ['view_activity', 'گزارش فعالیت']] },
  { title: 'پشتیبانی و اتصال', hint: 'پاسخ و اتصال رضایت‌محور', items: [['reply_support', 'پاسخ‌گویی پشتیبانی'], ['view_remote', 'اتصال امن به سیستم‌ها']] },
] as const;
const fallbackRoles: RoleDefinition[] = [
  { id: 0, code: 'member', name: 'کاربر فضای کاری', description: '', permissions: {}, is_system: true },
  { id: 0, code: 'support', name: 'کارشناس پشتیبانی', description: '', permissions: {}, is_system: true },
  { id: 0, code: 'auditor', name: 'حسابرس', description: '', permissions: {}, is_system: true },
  { id: 0, code: 'admin', name: 'مدیر سیستم', description: '', permissions: {}, is_system: true },
  { id: 0, code: 'owner', name: 'مالک سازمان', description: '', permissions: {}, is_system: true },
];
const gb = (bytes: number) => (bytes / 1024 ** 3).toFixed(2);
const initialUser = { username: '', password: '', first_name: '', last_name: '', quota_gb: '5' };

export function AdminPage() {
  const { user } = useAuth();
  const canManage = Boolean(user?.is_superuser || user?.is_staff || user?.role === 'owner' || user?.role === 'admin' || user?.permissions?.manage_users);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [agents, setAgents] = useState<SupportAgentPermission[]>([]);
  const [perfAgents, setPerfAgents] = useState<SupportAgentPerformance[]>([]);
  const [perfDays, setPerfDays] = useState(30);
  const [perfLoading, setPerfLoading] = useState(false);
  const [escalationInfo, setEscalationInfo] = useState('');
  const [roleDefs, setRoleDefs] = useState<RoleDefinition[]>([]);
  const [activeCode, setActiveCode] = useState('member');
  const [selectedRoles, setSelectedRoles] = useState<string[]>(['member']);
  const [quotaDraft, setQuotaDraft] = useState<Record<number, string>>({});
  const [createOpen, setCreateOpen] = useState(false);
  const [roleOpen, setRoleOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState<number | null>(null);
  const [form, setForm] = useState(initialUser);
  const [edit, setEdit] = useState({ first_name: '', last_name: '', phone: '', password: '', gender: 'male' });
  const [editRoles, setEditRoles] = useState<string[]>([]);
  const [roleForm, setRoleForm] = useState({ name: '', code: '', description: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const roles = roleDefs.length ? roleDefs : fallbackRoles;
  const activeRole = useMemo(() => roles.find(role => role.code === activeCode) ?? roles[0], [roles, activeCode]);
  const selectedRoleUsers = users.filter(item => (((item as AdminUser & { roles?: string[] }).roles ?? [item.role ?? 'member']).includes(activeRole?.code ?? '')));

  function announce(message: string) { setNotice(message); window.setTimeout(() => setNotice(''), 3600); }
  
  async function loadPerformance(days = perfDays) {
    if (!canManage) return;
    setPerfLoading(true);
    try {
      const data = await fetchSupportPerformance(days);
      setPerfAgents(data.agents || []);
      setPerfDays(data.days);
    } catch {
      setPerfAgents([]);
    } finally {
      setPerfLoading(false);
    }
  }

  async function handleRunEscalations() {
    try {
      const r = await runSupportEscalations();
      setEscalationInfo(`پیگیری‌ها: ${r.escalated} — اطلاع ادمین: ${r.admin_notified}`);
      await loadPerformance();
    } catch (e) {
      setEscalationInfo(e instanceof Error ? e.message : 'خطا در اجرای پیگیری');
    }
  }

function refresh() {
    Promise.all([listAdminUsers(), listSupportAgents(), listRoleDefinitions().catch(() => [] as RoleDefinition[])])
      .then(([accounts, supportAgents, definitions]) => { setUsers(accounts); setAgents(supportAgents); setRoleDefs(definitions); if (definitions.length && !definitions.some(role => role.code === activeCode)) setActiveCode(definitions[0].code); })
      .catch(reason => setError(reason instanceof Error ? reason.message : 'دریافت اطلاعات مدیریتی ناموفق بود.'));
  }
  useEffect(() => { if (canManage) { refresh(); void loadPerformance(); } }, [canManage]);

  async function savePermission(key: string, checked: boolean) {
    if (!activeRole?.id || (activeRole.is_system && !user?.is_superuser)) return;
    try {
      const updated = await updateRoleDefinition(activeRole.id, { permissions: { ...activeRole.permissions, [key]: checked } });
      setRoleDefs(items => items.map(item => item.id === activeRole.id ? { ...item, permissions: updated.permissions } : item));
      announce('مجوز نقش به‌روزرسانی شد.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'به‌روزرسانی نقش ناموفق بود.'); }
  }
  async function createUser(event: FormEvent) {
    event.preventDefault(); setCreating(true); setError('');
    try {
      await createAdminUser({ ...form, quota_gb: Number(form.quota_gb) || 5, role: selectedRoles[0] ?? 'member', roles: selectedRoles, is_staff: selectedRoles.some(role => ['owner', 'admin', 'support'].includes(role)) });
      setForm(initialUser); setSelectedRoles(['member']); setCreateOpen(false); announce('کاربر با سطح دسترسی انتخاب‌شده ایجاد شد.'); refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'ایجاد کاربر ناموفق بود.'); } finally { setCreating(false); }
  }
  async function createRole(event: FormEvent) {
    event.preventDefault();
    try {
      const created = await createRoleDefinition({ code: roleForm.code.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '-'), name: roleForm.name.trim(), description: roleForm.description.trim(), permissions: {} });
      setRoleDefs(items => [...items, created]); setActiveCode(created.code); setRoleForm({ name: '', code: '', description: '' }); setRoleOpen(false); announce('نقش جدید ایجاد شد؛ اکنون مجوزهای آن را تعیین کنید.');
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'ایجاد نقش ناموفق بود.'); }
  }
  async function saveQuota(account: AdminUser) {
    const value = quotaDraft[account.user] ?? gb(account.allocated_bytes); const bytes = Math.round(Number(value) * 1024 ** 3);
    if (!Number.isFinite(bytes) || bytes < account.used_bytes) { setError('سهمیه باید عددی معتبر و بیش‌تر از مصرف فعلی باشد.'); return; }
    setSaving(account.user);
    try { const updated = await updateUserQuota(account.user, bytes); setUsers(items => items.map(item => item.user === updated.user ? { ...item, ...updated } : item)); announce('سهمیه فضای کاری ذخیره شد.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'ذخیره سهمیه ناموفق بود.'); } finally { setSaving(null); }
  }
  async function changeRole(userId: number, role: string) {
    try { await updateUserRole(userId, role); setUsers(items => items.map(item => item.user === userId ? { ...item, role } : item)); announce('نقش اصلی کاربر به‌روزرسانی شد.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'تغییر نقش ناموفق بود.'); }
  }
  async function toggleAgent(agent: SupportAgentPermission) {
    try { const updated = await setSupportReplyPermission(agent.user, !agent.can_reply); setAgents(items => items.map(item => item.user === updated.user ? updated : item)); announce(updated.can_reply ? 'مجوز پاسخ‌گویی فعال شد.' : 'مجوز پاسخ‌گویی غیرفعال شد.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'تغییر مجوز ناموفق بود.'); }
  }
  function openEdit(account: AdminUser) {
    setEditId(account.user); setEdit({ first_name: account.first_name ?? '', last_name: account.last_name ?? '', phone: (account as AdminUser & { phone?: string }).phone ?? '', password: '', gender: (account as AdminUser & { gender?: string }).gender ?? 'male' });
    setEditRoles((account as AdminUser & { roles?: string[] }).roles ?? [account.role ?? 'member']);
  }
  async function saveEdit(event: FormEvent) {
    event.preventDefault(); if (!editId) return;
    try { const payload: Record<string, unknown> = { first_name: edit.first_name, last_name: edit.last_name, phone: edit.phone, gender: edit.gender, role: editRoles[0] ?? 'member', roles: editRoles }; if (edit.password) payload.password = edit.password; await updateAdminUser(editId, payload); setEditId(null); announce('مشخصات و نقش‌های کاربر به‌روزرسانی شد.'); refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'ویرایش کاربر ناموفق بود.'); }
  }
  function toggleRole(code: string, checked: boolean, setter: (roles: string[]) => void, current: string[]) { setter(checked ? [...current, code] : current.filter(role => role !== code)); }

  if (!canManage) return <div className="panel empty"><ShieldCheck size={28} /><h2>دسترسی مدیریتی لازم است</h2><p>این بخش فقط برای مدیران فعال است.</p></div>;
  return <div className="access-page">
    <section className="access-hero"><div className="access-hero__copy"><span className="section-kicker"><ShieldCheck size={15} />مرکز کنترل هویت</span><h1>سطح دسترسی‌ها، در یک نگاه</h1><p>نقش‌ها را تعریف کنید، محدوده هر نقش را دقیق ببینید و فضای کاری تیم را بدون ابهام اداره کنید.</p></div><div className="access-metrics"><div><UsersRound size={18} /><span>اعضای فعال</span><strong>{users.length}</strong></div><div><KeyRound size={18} /><span>نقش‌های تعریف‌شده</span><strong>{roles.length}</strong></div><div><BadgeCheck size={18} /><span>پشتیبان پاسخ‌گو</span><strong>{agents.filter(agent => agent.can_reply).length}</strong></div></div></section>
    {(error || notice) && <div className={`access-alert ${error ? 'is-error' : 'is-success'}`} role={error ? 'alert' : 'status'}>{error || notice}</div>}
    <section className="access-workbench"><aside className="role-rail"><div className="role-rail__head"><div><span className="section-kicker">نقش‌ها</span><h2>مدل دسترسی</h2></div><button className="icon-action" onClick={() => setRoleOpen(value => !value)} aria-label="افزودن نقش"><Plus size={18} /></button></div><div className="role-list">{roles.map(role => <button className={`role-list__item ${activeRole?.code === role.code ? 'is-active' : ''}`} onClick={() => setActiveCode(role.code)} key={role.code}><span className="role-list__badge">{role.name.slice(0, 1)}</span><span><b>{role.name}</b><small>{users.filter(item => (((item as AdminUser & { roles?: string[] }).roles ?? [item.role ?? 'member']).includes(role.code))).length} عضو</small></span><ChevronLeft size={16} /></button>)}</div>{roleOpen && <form className="role-creator" onSubmit={createRole}><div className="role-creator__head"><b>نقش تازه</b><button className="plain-icon" type="button" onClick={() => setRoleOpen(false)}><X size={16} /></button></div><input required placeholder="نام نمایشی" value={roleForm.name} onChange={event => setRoleForm(value => ({ ...value, name: event.target.value }))} /><input required dir="ltr" placeholder="کد انگلیسی نقش" value={roleForm.code} onChange={event => setRoleForm(value => ({ ...value, code: event.target.value }))} /><textarea rows={2} placeholder="توضیح کوتاه" value={roleForm.description} onChange={event => setRoleForm(value => ({ ...value, description: event.target.value }))} /><button className="secondary-action"><Plus size={15} />ساخت نقش</button></form>}</aside>
      <div className="permission-studio"><div className="permission-studio__head"><div><span className="section-kicker">دامنه نقش انتخاب‌شده</span><h2>{activeRole?.name}</h2><p>{activeRole?.description || 'محدوده‌های عملیاتی این نقش را برای سازمان تنظیم کنید.'}</p></div><span className={`system-pill ${activeRole?.is_system ? 'is-system' : ''}`}>{activeRole?.is_system ? 'نقش سیستمی' : 'نقش سفارشی'}</span></div><div className="permission-groups">{permissionGroups.map(group => <section className="permission-group" key={group.title}><div><h3>{group.title}</h3><p>{group.hint}</p></div><div className="permission-options">{group.items.map(([key, label]) => { const checked = Boolean(activeRole?.permissions?.[key]); const locked = Boolean(activeRole?.is_system && !user?.is_superuser); return <label className={`permission-toggle-card ${checked ? 'is-enabled' : ''} ${locked ? 'is-locked' : ''}`} key={key}><input type="checkbox" checked={checked} disabled={locked || !activeRole?.id} onChange={event => void savePermission(key, event.target.checked)} /><span className="toggle-indicator">{checked && <Check size={13} />}</span><span>{label}</span></label>; })}</div></section>)}</div>{activeRole?.is_system && !user?.is_superuser && <div className="lock-note"><ShieldCheck size={16} />این نقش سیستمی است؛ تغییر آن فقط برای مالک سازمان امکان‌پذیر است.</div>}<div className="role-summary"><UsersRound size={18} /><span>کاربران دارای این نقش</span><strong>{selectedRoleUsers.length}</strong></div></div></section>
    <section className="access-operations"><div className="member-directory panel"><div className="panel-head compact"><div><span className="section-kicker">فهرست اعضا</span><h2>کاربران و سهمیه فضای کاری</h2><p>سطح دسترسی، ظرفیت و مشخصات اعضا را از یک نقطه مدیریت کنید.</p></div><button className="primary" onClick={() => setCreateOpen(value => !value)}><UserPlus size={16} />{createOpen ? 'بستن فرم' : 'افزودن کاربر'}</button></div>{createOpen && <form className="user-create-form" onSubmit={createUser}><label><span>نام کاربری</span><input required value={form.username} onChange={event => setForm(value => ({ ...value, username: event.target.value }))} /></label><label><span>رمز عبور</span><input required type="password" value={form.password} onChange={event => setForm(value => ({ ...value, password: event.target.value }))} /></label><label><span>نام</span><input value={form.first_name} onChange={event => setForm(value => ({ ...value, first_name: event.target.value }))} /></label><label><span>نام خانوادگی</span><input value={form.last_name} onChange={event => setForm(value => ({ ...value, last_name: event.target.value }))} /></label><label><span>سهمیه (GB)</span><input type="number" min="0.5" step="0.5" value={form.quota_gb} onChange={event => setForm(value => ({ ...value, quota_gb: event.target.value }))} /></label><fieldset><legend>نقش‌ها</legend><div>{roles.map(role => <label className="check-chip" key={role.code}><input type="checkbox" checked={selectedRoles.includes(role.code)} onChange={event => toggleRole(role.code, event.target.checked, setSelectedRoles, selectedRoles)} />{role.name}</label>)}</div></fieldset><button className="primary user-create-form__submit" disabled={creating}>{creating ? 'در حال ایجاد…' : 'ایجاد کاربر'}</button></form>}<div className="member-table">{users.map(account => { const used = Math.min(100, Math.max(0, account.percent_used)); const accountRoles = (account as AdminUser & { roles?: string[] }).roles ?? [account.role ?? 'member']; return <article className="member-row" key={account.user}><div className="member-row__identity"><span className="member-avatar">{(account.first_name || account.username || '?').slice(0, 1)}</span><div><b>{account.first_name || account.username} {account.last_name || ''}</b><small>@{account.username}</small><div className="role-chip-row">{accountRoles.map(role => <span key={role}>{roleLabels[role] ?? role}</span>)}</div></div></div><div className="member-row__storage"><div><span><HardDrive size={14} />فضای کاری</span><strong>{gb(account.used_bytes)} / {gb(account.allocated_bytes)} GB</strong></div><div className="storage-meter"><i style={{ width: `${used}%` }} /></div></div><div className="member-row__actions">{user?.is_superuser && <select value={account.role ?? 'member'} onChange={event => void changeRole(account.user, event.target.value)}>{roles.map(role => <option value={role.code} key={role.code}>{role.name}</option>)}</select>}<div className="quota-input"><input type="number" min={gb(account.used_bytes)} step="0.5" value={quotaDraft[account.user] ?? gb(account.allocated_bytes)} onChange={event => setQuotaDraft(items => ({ ...items, [account.user]: event.target.value }))} /><span>GB</span></div><button className="subtle-action" disabled={saving === account.user} onClick={() => void saveQuota(account)}>{saving === account.user ? '…' : 'ذخیره'}</button><button className="icon-action" onClick={() => openEdit(account)}><UserCog size={17} /></button></div></article>; })}</div></div><aside className="support-permission-card"><div className="support-permission-card__icon"><SlidersHorizontal size={20} /></div><span className="section-kicker">واحد پشتیبانی</span><h2>اجازه پاسخ‌گویی</h2><p>فقط افراد تأییدشده می‌توانند به گفت‌وگوهای مشتریان پاسخ دهند.</p><div className="support-agent-list">{agents.length ? agents.map(agent => <div className="support-agent" key={agent.user}><span>{agent.username.slice(0, 1)}</span><div><b>{agent.username}</b><small>{agent.can_reply ? 'پاسخ‌گویی فعال' : 'نیازمند تأیید'}</small></div><button className={`mini-switch ${agent.can_reply ? 'is-on' : ''}`} onClick={() => void toggleAgent(agent)}><i /></button></div>) : <p className="muted">هنوز کارشناس پشتیبانی در فهرست نیست.</p>}</div></aside></section>
    
    <section className="panel" style={{ marginTop: 24 }}>
      <div className="panel-head">
        <div>
          <span className="section-kicker">عملکرد پشتیبانی</span>
          <h2>امتیاز و فعالیت کارشناسان</h2>
          <p>بر اساس پاسخ‌ها، زمان اولین پاسخ، escalation و حضور آنلاین.</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select value={perfDays} onChange={e => { const d = Number(e.target.value); setPerfDays(d); void loadPerformance(d); }}>
            <option value={7}>۷ روز</option>
            <option value={30}>۳۰ روز</option>
            <option value={90}>۹۰ روز</option>
          </select>
          <button type="button" className="ghost" onClick={() => void loadPerformance()} disabled={perfLoading}>
            <RefreshCw size={14} /> بروزرسانی
          </button>
          <button type="button" className="ghost" onClick={() => void handleRunEscalations()}>
            <Activity size={14} /> اجرای پیگیری معوق
          </button>
        </div>
      </div>
      {escalationInfo && <p className="muted" style={{ marginBottom: 12 }}>{escalationInfo}</p>}
      {perfLoading ? <p className="muted">بارگذاری گزارش...</p> : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: 'right', color: 'var(--muted)' }}>
                <th style={{ padding: 8 }}>کارشناس</th>
                <th style={{ padding: 8 }}>آنلاین</th>
                <th style={{ padding: 8 }}>پاسخ‌ها</th>
                <th style={{ padding: 8 }}>مکالمات</th>
                <th style={{ padding: 8 }}>میانگین اولین پاسخ</th>
                <th style={{ padding: 8 }}>پیگیری‌ها</th>
                <th style={{ padding: 8 }}>امتیاز</th>
              </tr>
            </thead>
            <tbody>
              {perfAgents.length === 0 ? (
                <tr><td colSpan={7} style={{ padding: 12 }} className="muted">داده‌ای برای بازه انتخابی نیست.</td></tr>
              ) : perfAgents.map(row => (
                <tr key={row.user_id} style={{ borderTop: '1px solid #ffffff12' }}>
                  <td style={{ padding: 8 }}><b>{row.full_name}</b><div className="muted" style={{ fontSize: 11 }}>{row.username}</div></td>
                  <td style={{ padding: 8 }}>{row.is_online_now ? '● بله' : '○ خیر'}</td>
                  <td style={{ padding: 8 }}>{row.reply_count}</td>
                  <td style={{ padding: 8 }}>{row.conversations_touched}</td>
                  <td style={{ padding: 8 }}>{row.avg_first_response_seconds != null ? `${Math.round(row.avg_first_response_seconds / 60)} دقیقه` : '—'}</td>
                  <td style={{ padding: 8 }}>{row.escalations}</td>
                  <td style={{ padding: 8 }}><b style={{ color: row.score >= 70 ? '#3cc78b' : row.score >= 40 ? '#e6b84d' : '#e07a7a' }}>{row.score}</b></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
    {editId && <section className="edit-drawer"><div className="edit-drawer__backdrop" onClick={() => setEditId(null)} /><form className="edit-drawer__panel" onSubmit={saveEdit}><div className="edit-drawer__head"><div><span className="section-kicker">ویرایش عضو</span><h2>مشخصات و دسترسی‌ها</h2></div><button className="icon-action" type="button" onClick={() => setEditId(null)}><X size={18} /></button></div><div className="edit-grid"><label><span>نام</span><input value={edit.first_name} onChange={event => setEdit(value => ({ ...value, first_name: event.target.value }))} /></label><label><span>نام خانوادگی</span><input value={edit.last_name} onChange={event => setEdit(value => ({ ...value, last_name: event.target.value }))} /></label><label><span>موبایل</span><input value={edit.phone} onChange={event => setEdit(value => ({ ...value, phone: event.target.value }))} /></label><label><span>رمز جدید</span><input type="password" value={edit.password} onChange={event => setEdit(value => ({ ...value, password: event.target.value }))} /></label><label><span>جنسیت</span><select value={edit.gender} onChange={event => setEdit(value => ({ ...value, gender: event.target.value }))}><option value="male">مرد</option><option value="female">زن</option><option value="other">سایر</option></select></label></div><fieldset className="edit-role-fieldset"><legend>نقش‌های کاربر</legend><div>{roles.map(role => <label className="check-chip" key={role.code}><input type="checkbox" checked={editRoles.includes(role.code)} onChange={event => toggleRole(role.code, event.target.checked, setEditRoles, editRoles)} />{role.name}</label>)}</div></fieldset><button className="primary">ذخیره تغییرات</button></form></section>}
  </div>;
}
