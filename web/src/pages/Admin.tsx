import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api, normalizeS3 } from '../lib/api';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type User = { id: number; email: string; org_id?: number | null; roles: string[] };

const ALL_ROLES = ['superadmin', 'org_admin', 'designer', 'researcher', 'reviewer'];

export default function AdminPage() {
  const [me, setMe] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRoles, setNewRoles] = useState<string[]>(['designer']);
  const [projName, setProjName] = useState('');
  const [projDesc, setProjDesc] = useState('');
  const [pwEdits, setPwEdits] = useState<Record<number, string>>({});
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string } | null>(null);
  const [projects, setProjects] = useState<Array<{ id:number; name:string; description?: string }>>([]);
  const [selectedProject, setSelectedProject] = useState<number | ''>('');
  const [projMembers, setProjMembers] = useState<Array<User>>([]);
  const [projEditName, setProjEditName] = useState('');
  const [projEditDesc, setProjEditDesc] = useState('');
  const [addUserId, setAddUserId] = useState<number | ''>('');
  const [projScenarios, setProjScenarios] = useState<Array<{ id:number; name:string }>>([]);
  const [projArtifacts, setProjArtifacts] = useState<Array<{ id:number; name:string; presigned_url?: string }>>([]);
  const [rulepacks, setRulepacks] = useState<Array<{ id:number; name:string; version?: string }>>([]);
  const [runScenarioId, setRunScenarioId] = useState<number | ''>('');
  const [runRulepackId, setRunRulepackId] = useState<number | ''>('');
  const [reportEvalId, setReportEvalId] = useState<string>('');
  const [reportBusy, setReportBusy] = useState(false);
  const [reportLink, setReportLink] = useState<string | null>(null);

  async function load() {
    try {
      const u = await api.users.me();
      setMe(u);
      try {
        const list = await api.users.list();
        setUsers(list);
      } catch (e: any) {
        // not fatal (may be 403 for non-admins)
      }
      try {
        const projs = await api.projects.list();
        setProjects(projs);
        if (!selectedProject && projs.length) {
          setSelectedProject(projs[0].id);
          setProjEditName(projs[0].name || '');
          setProjEditDesc(projs[0].description || '');
          const pid = projs[0].id;
          const mem = await api.projects.members.list(pid);
          setProjMembers(mem);
          try {
            const scs = await api.scenarios.list(pid);
            setProjScenarios(scs);
            setRunScenarioId(scs[0]?.id || '');
          } catch {}
          try {
            const arts = await api.artifacts.list(pid);
            setProjArtifacts(arts);
          } catch {}
        } else if (selectedProject) {
          const p = projs.find(p=>p.id===selectedProject);
          if (p) { setProjEditName(p.name||''); setProjEditDesc(p.description||''); }
          const pid = Number(selectedProject);
          const mem = await api.projects.members.list(pid);
          setProjMembers(mem);
          try {
            const scs = await api.scenarios.list(pid);
            setProjScenarios(scs);
            setRunScenarioId(scs[0]?.id || '');
          } catch {}
          try {
            const arts = await api.artifacts.list(pid);
            setProjArtifacts(arts);
          } catch {}
        }
      } catch (e: any) { /* ignore */ }
      try {
        const rps = await api.rulepacks.list();
        setRulepacks(rps);
        if (!runRulepackId && rps.length) setRunRulepackId(rps[0].id);
      } catch {}
    } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { void load(); }, []);

  function toggleRole(target: User, role: string, on: boolean): string[] {
    const set = new Set(target.roles || []);
    if (on) set.add(role); else set.delete(role);
    return Array.from(set);
  }

  return (
    <Layout>
      <h1>Admin</h1>
      {err && <div className="muted" role="alert">{err}</div>}
      <div className="space" />
      {me && (
        <div className="panel">
          <h2>Me</h2>
          <div>Email: {me.email}</div>
          <div>Org: {me.org_id ?? '—'}</div>
          <div>Roles: {(me.roles || []).join(', ') || '—'}</div>
        </div>
      )}
      <div className="space" />
      {users.length > 0 && (
        <div className="panel">
          <h2>Users</h2>
          <div className="muted">Create users and manage roles/passwords (org_admin or superadmin).</div>
          <form
            onSubmit={async (e) => {
              e.preventDefault(); setErr(null);
              try {
                const created = await api.auth.register(newEmail.trim(), newPassword, me?.org_id || undefined);
                const target = users.find(u => u.email === newEmail.trim());
                // Set roles for the new user
                if (created?.access_token || true) {
                  // We don't need the token; we set roles via admin endpoint
                  const list = await api.users.list();
                  const nu = list.find(u => u.email === newEmail.trim());
                  if (nu) {
                    await api.users.setRoles(nu.id, newRoles);
                  }
                }
                setNewEmail(''); setNewPassword(''); setNewRoles(['designer']);
                const list2 = await api.users.list(); setUsers(list2);
                setToast({ msg: 'User created' });
              } catch (e: any) { setErr(e.message); }
            }}
            aria-label="Create user"
          >
            <h3>Create User</h3>
            <label htmlFor="ue">Email</label>
            <input id="ue" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} required />
            <label htmlFor="up">Password</label>
            <input id="up" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required />
            <div className="space" />
            <div>
              {ALL_ROLES.map(r => (
                <label key={r} style={{ marginRight: 8 }}>
                  <input
                    type="checkbox"
                    checked={newRoles.includes(r)}
                    onChange={(e) => {
                      setNewRoles(prev => {
                        const s = new Set(prev);
                        if (e.target.checked) s.add(r); else s.delete(r);
                        return Array.from(s);
                      });
                    }}
                  /> {r}
                </label>
              ))}
            </div>
            <div className="space" />
            <button type="submit">Create</button>
          </form>
          <div className="space" />
          <table className="table" role="table" aria-label="Users">
            <thead><tr><th>ID</th><th>Email</th><th>Org</th><th>Roles</th><th>Update</th><th>Reset Password</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.email}</td>
                  <td>{u.org_id ?? ''}</td>
                  <td>
                    {ALL_ROLES.map((r) => (
                      <label key={r} style={{ marginRight: 8 }}>
                        <input
                          type="checkbox"
                          checked={u.roles?.includes(r) || false}
                          onChange={(e) => {
                            const roles = toggleRole(u, r, e.target.checked);
                            setUsers((prev) => prev.map((x) => x.id === u.id ? { ...x, roles } : x));
                          }}
                        /> {r}
                      </label>
                    ))}
                  </td>
                  <td>
                    <button
                      onClick={async () => {
                        try {
                          const updated = await api.users.setRoles(u.id, u.roles || []);
                          setUsers((prev) => prev.map((x) => x.id === u.id ? updated : x));
                          setToast({ msg: 'Roles updated' });
                        } catch (e: any) { setErr(e.message); }
                      }}
                    >Save</button>
                  </td>
                  <td>
                    <input type="password" placeholder="New password" value={pwEdits[u.id] || ''} onChange={(e) => setPwEdits((prev) => ({ ...prev, [u.id]: e.target.value }))} style={{ width: 160 }} />
                    <button className="btn btn-outline" onClick={async () => {
                      try {
                        const pw = pwEdits[u.id];
                        if (!pw) { setErr('Password required'); return; }
                        await api.users.setPassword(u.id, pw);
                        setPwEdits((prev) => ({ ...prev, [u.id]: '' }));
                        setToast({ msg: 'Password updated' });
                      } catch (e: any) { setErr(e.message); }
                    }}>Set</button>
                  </td>
                  <td>
                    <button className="btn btn-danger" onClick={() => setPendingDelete(u.id)} disabled={me?.id === u.id}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted">Note: Only org_admin can manage users in their org; superadmin can manage all.</div>
        </div>
      )}
      <div className="space" />
      <div className="panel">
        <h2>Create Project</h2>
        <form onSubmit={async (e) => { e.preventDefault(); setErr(null); try { await api.projects.create(projName, projDesc || undefined); setProjName(''); setProjDesc(''); setToast({ msg: 'Project created' }); await load(); } catch (e: any) { setErr(e.message); } }} aria-label="Create project (admin)">
          <label htmlFor="pn2">Name</label>
          <input id="pn2" value={projName} onChange={(e) => setProjName(e.target.value)} required />
          <label htmlFor="pd2">Description</label>
          <input id="pd2" value={projDesc} onChange={(e) => setProjDesc(e.target.value)} />
          <div className="space" />
          <button type="submit" className="btn btn-primary">Create</button>
        </form>
      </div>
      <div className="space" />
      <div className="panel">
        <h2>Project Management</h2>
        <label htmlFor="pjSel">Select Project</label>
        <select id="pjSel" value={selectedProject || ''} onChange={async (e) => {
          const v = e.target.value ? Number(e.target.value) : '';
          setSelectedProject(v as any);
          if (v) {
            const p = projects.find(p=>p.id===v);
            setProjEditName(p?.name || '');
            setProjEditDesc(p?.description || '');
            const mem = await api.projects.members.list(v);
            setProjMembers(mem);
            try {
              const scs = await api.scenarios.list(v);
              setProjScenarios(scs);
              setRunScenarioId(scs[0]?.id || '');
            } catch {}
            try {
              const arts = await api.artifacts.list(v);
              setProjArtifacts(arts);
            } catch {}
          } else {
            setProjEditName(''); setProjEditDesc(''); setProjMembers([]); setProjScenarios([]); setProjArtifacts([]);
          }
        }}>
          <option value="">-- choose --</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name} (#{p.id})</option>)}
        </select>
        <div className="space" />
        {selectedProject && (
          <>
            <h3>Edit</h3>
            <form onSubmit={async (e) => { e.preventDefault(); try { await api.projects.update(Number(selectedProject), projEditName, projEditDesc || undefined); setToast({ msg: 'Project updated' }); await load(); } catch (e:any){ setErr(e.message); } }}>
              <label htmlFor="pje">Name</label>
              <input id="pje" value={projEditName} onChange={(e)=>setProjEditName(e.target.value)} required />
              <label htmlFor="pjd">Description</label>
              <input id="pjd" value={projEditDesc} onChange={(e)=>setProjEditDesc(e.target.value)} />
              <div className="space" />
              <button className="btn btn-primary" type="submit">Save</button>
            </form>
            <div className="space" />
            <h3>Members</h3>
            <ul>
              {projMembers.map(u => (
                <li key={u.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                  <span>{u.email} (#{u.id})</span>
                  <button className="btn btn-outline" onClick={async()=>{ try{ await api.projects.members.remove(Number(selectedProject), u.id); const mem = await api.projects.members.list(Number(selectedProject)); setProjMembers(mem); setToast({ msg: 'User removed' }); } catch(e:any){ setErr(e.message);} }}>Remove</button>
                </li>
              ))}
            </ul>
            <div className="row">
              <select value={addUserId || ''} onChange={(e)=>setAddUserId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">-- add user --</option>
                {users.filter(u => !projMembers.find(m=>m.id===u.id)).map(u => (
                  <option key={u.id} value={u.id}>{u.email} (#{u.id})</option>
                ))}
              </select>
              <button className="btn" onClick={async()=>{ if(!addUserId) return; try{ await api.projects.members.add(Number(selectedProject), Number(addUserId)); const mem = await api.projects.members.list(Number(selectedProject)); setProjMembers(mem); setAddUserId(''); setToast({ msg: 'User added' }); } catch(e:any){ setErr(e.message);} }}>Add</button>
            </div>
            <div className="space" />
            <h3>Scenarios</h3>
            <ul>
              {projScenarios.map(s => (<li key={s.id}>{s.name} (#{s.id})</li>))}
            </ul>
            <div className="space" />
            <h3>Artifacts</h3>
            <div className="row">
              <label htmlFor="scSelAdmin">Scenario</label>
              <select id="scSelAdmin" value={runScenarioId || ''} onChange={(e)=>setRunScenarioId(e.target.value?Number(e.target.value):'')}>
                <option value="">-- choose --</option>
                {projScenarios.map(s => <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>)}
              </select>
              <label htmlFor="rpSelAdmin">Rulepack</label>
              <select id="rpSelAdmin" value={runRulepackId || ''} onChange={(e)=>setRunRulepackId(e.target.value?Number(e.target.value):'')}>
                <option value="">-- choose --</option>
                {rulepacks.map(rp => <option key={rp.id} value={rp.id}>{rp.name}{rp.version?` v${rp.version}`:''} (#{rp.id})</option>)}
              </select>
            </div>
            <ul>
              {projArtifacts.map(a => (
                <li key={a.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                  <span>{a.name} (#{a.id})</span>
                  <div className="row">
                    {a.presigned_url && <a className="btn btn-outline" href={normalizeS3(a.presigned_url)} target="_blank" rel="noreferrer">Open</a>}
                    <button className="btn" disabled={!runScenarioId || !runRulepackId} onClick={async()=>{
                      try {
                        const r = await api.evaluations.enqueue(a.id, Number(runScenarioId), Number(runRulepackId));
                        setToast({ msg: `Evaluation ${r.id} enqueued` });
                      } catch (e:any) { setErr(e.message); }
                    }}>Run</button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
      <div className="space" />
      <div className="panel">
        <h2>Reports</h2>
        <div className="row" style={{ alignItems:'flex-end', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <label htmlFor="revid">Evaluation ID</label>
            <input id="revid" value={reportEvalId} onChange={(e)=>setReportEvalId(e.target.value)} placeholder="e.g. 123" />
          </div>
          <div>
            <button className="btn" disabled={!reportEvalId || reportBusy} onClick={async()=>{
              try {
                setReportBusy(true);
                const rep = await api.evaluations.report(Number(reportEvalId));
                const url = normalizeS3(rep?.presigned_pdf_url || rep?.presigned_html_url);
                if (url) {
                  setReportLink(url);
                  window.open(url, '_blank');
                }
              } catch (e:any) { setErr(e.message); }
              finally { setReportBusy(false); }
            }}>{reportBusy ? 'Generating…' : 'Generate & Open'}</button>
          </div>
        </div>
        {reportLink && (
          <>
            <div className="space" />
            <div><strong>Last report:</strong> <a href={reportLink} target="_blank" rel="noreferrer">Open</a></div>
          </>
        )}
      </div>
      <Confirm
        open={pendingDelete !== null}
        title="Delete user?"
        message="This action cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            await api.users.delete(pendingDelete);
            setPendingDelete(null);
            const list = await api.users.list();
            setUsers(list);
            setToast({ msg: 'User deleted' });
          } catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && <Toast message={toast.msg} onClose={() => setToast(null)} />}
    </Layout>
  );
}
