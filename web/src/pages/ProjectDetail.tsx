import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api, normalizeS3 } from '../lib/api';
import { href } from '../router';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type Project = { id: number; name: string; description?: string };
type User = { id: number; email: string; org_id?: number | null; roles: string[] };

export default function ProjectDetailPage({ id }: { id: number }) {
  const [project, setProject] = useState<Project | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [tab, setTab] = useState<'artifacts' | 'scenarios' | 'reports' | 'users' | 'edit' | 'danger'>('artifacts');
  const [scenarios, setScenarios] = useState<Array<{ id:number; name:string }>>([]);
  const [newScenName, setNewScenName] = useState('');
  const [newScenConfig, setNewScenConfig] = useState('');
  const [pendingScenarioDelete, setPendingScenarioDelete] = useState<number | null>(null);
  const [artifacts, setArtifacts] = useState<Array<{ id:number; name:string; presigned_url?: string }>>([]);
  const [members, setMembers] = useState<User[]>([]);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [addUserId, setAddUserId] = useState<number | ''>('');
  const [toast, setToast] = useState<{ msg: string } | null>(null);
  const [rulepacks, setRulepacks] = useState<Array<{ id:number; name:string; version?:string }>>([]);
  const [reports, setReports] = useState<Array<{ id:number; title:string; presigned_html_url?:string; presigned_pdf_url?:string; created_at?: string }>>([]);
  const [busyEvalId, setBusyEvalId] = useState<number | null>(null);
  const [convBusyId, setConvBusyId] = useState<number | null>(null);
  const [selScenario, setSelScenario] = useState<Record<number, number | ''>>({});
  const [selRulepack, setSelRulepack] = useState<Record<number, number | ''>>({});
  async function pollEvaluation(eid: number, maxMs = 60000, intervalMs = 1000): Promise<any | null> {
    const deadline = Date.now() + maxMs;
    while (Date.now() < deadline) {
      try {
        const ev = await api.evaluations.get(eid);
        if (ev?.status === 'done') return ev;
      } catch {}
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    return null;
  }
  const [evaluations, setEvaluations] = useState<Array<{ id:number; status:string; created_at?:string; metrics?: any }>>([]);
  async function loadReports() {
    try {
      const reps = await api.projects.reports.list(id);
      setReports(reps || []);
    } catch (e:any) { setErr(e.message); }
  }
  // Inline uploader state
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upParams, setUpParams] = useState<File | null>(null);
  const [upName, setUpName] = useState('');
  const [upBusy, setUpBusy] = useState(false);
  useEffect(() => {
    (async () => {
      try {
        const p = await api.projects.get(id);
        setProject(p);
        setName(p.name || '');
        setDesc(p.description || '');
        try {
          const scs = await api.scenarios.list(id);
          setScenarios(scs);
        } catch {}
        try {
          const arts = await api.artifacts.list(id);
          setArtifacts(arts);
        } catch {}
        try {
          const rps = await api.rulepacks.list();
          setRulepacks(rps);
        } catch {}
        try { await loadReports(); } catch {}
        try {
          const evals = await api.projects.evaluations.list(id);
          setEvaluations(evals || []);
        } catch {}
        try {
          const mem = await api.projects.members.list(id);
          setMembers(mem);
        } catch {}
        try {
          const users = await api.users.list();
          setAllUsers(users);
        } catch {}
      } catch (e: any) { setErr(e.message); }
    })();
  }, [id]);

  return (
    <Layout>
      {!project ? <div>Loading...</div> : (
        <>
          <h1>{project.name}</h1>
          {project.description && <div className="muted">{project.description}</div>}
          <div className="space" />
          <nav className="row" role="tablist" aria-label="Project tabs" style={{ gap: 8 }}>
            <button className="btn" aria-selected={tab==='artifacts'} onClick={()=>setTab('artifacts')}>Artifacts</button>
            <button className="btn" aria-selected={tab==='scenarios'} onClick={()=>setTab('scenarios')}>Scenarios</button>
            <button className="btn" aria-selected={tab==='evaluations'} onClick={()=>setTab('evaluations')}>Evaluations</button>
            <button className="btn" aria-selected={tab==='reports'} onClick={()=>{ setTab('reports'); if (!reports.length) { void loadReports(); } }}>Reports</button>
            <button className="btn" aria-selected={tab==='users'} onClick={()=>setTab('users')}>Users</button>
            <button className="btn" aria-selected={tab==='edit'} onClick={()=>setTab('edit')}>Edit</button>
            <button className="btn btn-danger" aria-selected={tab==='danger'} onClick={()=>setTab('danger')}>Danger</button>
          </nav>
          <div className="space" />
          {tab === 'artifacts' && (
            <>
              <h2>Artifacts</h2>
              <h3>Create Artifact</h3>
              <div className="panel">
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setErr(null);
                    if (!upFile) { setErr('Choose a file'); return; }
                    setUpBusy(true);
                    try {
                      const res = await api.artifacts.upload(id, upFile, upParams ?? undefined, upName || upFile.name);
                      const normalized = { ...res, presigned_url: normalizeS3(res.presigned_url) };
                      setArtifacts((prev) => [normalized as any, ...prev]);
                      if (normalized.presigned_url) {
                        sessionStorage.setItem(`artifact_url_${res.id}`, normalized.presigned_url as string);
                      }
                      setUpFile(null); setUpParams(null); setUpName('');
                      setToast({ msg: 'Artifact uploaded' });
                    } catch (e:any) { setErr(e.message); }
                    finally { setUpBusy(false); }
                  }}
                  aria-label="Inline artifact uploader"
                >
                  <div className="row" style={{ alignItems: 'flex-end', flexWrap: 'wrap', gap: 12 }}>
                    <div>
                      <label htmlFor="f3d">3D File</label>
                      <input id="f3d" type="file" accept=".gltf,.glb,.stp,.step" onChange={(e)=>setUpFile(e.target.files?.[0] ?? null)} />
                    </div>
                    <div>
                      <label htmlFor="fjson">Params (JSON, optional)</label>
                      <input id="fjson" type="file" accept="application/json" onChange={(e)=>setUpParams(e.target.files?.[0] ?? null)} />
                    </div>
                    <div style={{ minWidth: 240, flex: 1 }}>
                      <label htmlFor="fname">Name</label>
                      <input id="fname" value={upName} onChange={(e)=>setUpName(e.target.value)} placeholder="Optional" />
                    </div>
                    <div>
                      <button className="btn" type="submit" disabled={upBusy}>Upload</button>
                    </div>
                  </div>
                </form>
                <div className="space" />
                <a className="btn btn-outline" href={href({ name: 'artifacts', id })}>Open full uploader</a>
              </div>
              <div className="space" />
              <h3>Uploaded Artifacts</h3>
              <ul>
                {artifacts.map((a) => (
                  <li key={a.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                    <span>{a.name} (#{a.id})</span>
                    <div className="row">
                      <label htmlFor={`sc-sel-${a.id}`}>Scenario</label>
                      <select id={`sc-sel-${a.id}`} value={selScenario[a.id] ?? (scenarios[0]?.id || '')} onChange={(e)=> setSelScenario((prev)=> ({ ...prev, [a.id]: e.target.value ? Number(e.target.value) : '' }))}>
                        <option value="">-- choose --</option>
                        {scenarios.map((s) => (<option key={s.id} value={s.id}>{s.name} (#{s.id})</option>))}
                      </select>
                      <label htmlFor={`rp-sel-${a.id}`}>RulePack</label>
                      <select id={`rp-sel-${a.id}`} value={selRulepack[a.id] ?? (rulepacks[0]?.id || '')} onChange={(e)=> setSelRulepack((prev)=> ({ ...prev, [a.id]: e.target.value ? Number(e.target.value) : '' }))}>
                        <option value="">-- choose --</option>
                        {rulepacks.map((rp) => (<option key={rp.id} value={rp.id}>{rp.name}{rp.version?` v${rp.version}`:''} (#{rp.id})</option>))}
                      </select>
                      {a.type && a.type !== 'gltf' && a.type !== 'glb' && (
                        <button
                          className="btn"
                          disabled={convBusyId === a.id}
                          onClick={async ()=>{
                            try {
                              setConvBusyId(a.id);
                              await api.artifacts.convert(a.id);
                              const deadline = Date.now() + 60000;
                              while (Date.now() < deadline) {
                                const art = await api.artifacts.get(a.id);
                                if (art?.type && (art.type === 'gltf' || art.type === 'glb') && art.presigned_url) {
                                  const url = normalizeS3(art.presigned_url);
                                  setArtifacts(prev => prev.map(x => x.id === a.id ? { ...x, type: art.type, presigned_url: url } : x));
                                  setToast({ msg: 'Artifact converted to glTF' });
                                  break;
                                }
                                await new Promise(r => setTimeout(r, 1500));
                              }
                            } catch (e:any) { setErr(e.message); }
                            finally { setConvBusyId(null); }
                          }}
                        >{convBusyId === a.id ? 'Converting…' : 'Convert to glTF'}</button>
                      )}
                      {a.presigned_url && <a className="btn btn-outline" href={normalizeS3(a.presigned_url)} target="_blank" rel="noreferrer">Open</a>}
                      {a.presigned_url && <a className="btn" href={normalizeS3(a.presigned_url)} download>Download</a>}
                      <button
                        className="btn"
                        onClick={async()=>{
                          try {
                          if (!scenarios.length) { setErr('Create a scenario first'); return; }
                          const scenarioId = (selScenario[a.id] ?? scenarios[0]?.id) as number;
                          const rpId = (selRulepack[a.id] ?? rulepacks[0]?.id) as number;
                            if (!rpId) { setErr('No rulepack available'); return; }
                            const r = await api.evaluations.enqueue(a.id, scenarioId, rpId);
                            setToast({ msg: `Evaluation ${r.id} enqueued` });
                          } catch (e:any) { setErr(e.message); }
                        }}
                      >Run</button>
                      <button
                        className="btn"
                        disabled={busyEvalId === a.id}
                        onClick={async()=>{
                          try {
                          if (!scenarios.length) { setErr('Create a scenario first'); return; }
                          const scenarioId = (selScenario[a.id] ?? scenarios[0]?.id) as number;
                          const rpId = (selRulepack[a.id] ?? rulepacks[0]?.id) as number;
                            if (!rpId) { setErr('No rulepack available'); return; }
                            setBusyEvalId(a.id);
                            const r = await api.evaluations.enqueue(a.id, scenarioId, rpId);
                            const done = await pollEvaluation(r.id, 120000, 1500);
                            if (!done) { setErr('Timed out waiting for evaluation'); setBusyEvalId(null); return; }
                            const rep = await api.evaluations.report(done.id);
                            const url = normalizeS3(rep?.presigned_pdf_url || rep?.presigned_html_url);
                            if (url) { window.open(url, '_blank'); }
                            await loadReports();
                            setToast({ msg: `Report generated for eval ${done.id}` });
                          } catch (e:any) { setErr(e.message); }
                          finally { setBusyEvalId(null); }
                        }}
                      >{busyEvalId === a.id ? 'Running…' : 'Run & Report'}</button>
                      <button
                        className="btn btn-danger"
                        onClick={async()=>{
                          try {
                            await api.artifacts.delete(id, a.id);
                            setArtifacts(prev => prev.filter(x => x.id !== a.id));
                            sessionStorage.removeItem(`artifact_url_${a.id}`);
                            setToast({ msg: 'Artifact deleted' });
                          } catch (e:any) { setErr(e.message); }
                        }}
                      >Delete</button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
          {tab === 'evaluations' && (
            <>
              <h2>Evaluations</h2>
              {artifacts.length === 0 && (
                <div className="muted">No artifacts yet. Upload an artifact in the Artifacts tab.</div>
              )}
              {(!scenarios || scenarios.length === 0) && (
                <div className="muted">No scenarios. Create a scenario in the Scenarios tab.</div>
              )}
              {(!rulepacks || rulepacks.length === 0) && (
                <div className="muted">No rulepacks. Create or seed a rulepack first.</div>
              )}
              <ul>
                {artifacts.map((a) => (
                  <li key={a.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 6 }}>
                    <span>{a.name} (#{a.id})</span>
                    <div className="row">
                      <label htmlFor={`ev-sc-sel-${a.id}`}>Scenario</label>
                      <select id={`ev-sc-sel-${a.id}`} value={selScenario[a.id] ?? (scenarios[0]?.id || '')} onChange={(e)=> setSelScenario((prev)=> ({ ...prev, [a.id]: e.target.value ? Number(e.target.value) : '' }))}>
                        <option value="">-- choose --</option>
                        {scenarios.map((s) => (<option key={s.id} value={s.id}>{s.name} (#{s.id})</option>))}
                      </select>
                      <label htmlFor={`ev-rp-sel-${a.id}`}>RulePack</label>
                      <select id={`ev-rp-sel-${a.id}`} value={selRulepack[a.id] ?? (rulepacks[0]?.id || '')} onChange={(e)=> setSelRulepack((prev)=> ({ ...prev, [a.id]: e.target.value ? Number(e.target.value) : '' }))}>
                        <option value="">-- choose --</option>
                        {rulepacks.map((rp) => (<option key={rp.id} value={rp.id}>{rp.name}{rp.version?` v${rp.version}`:''} (#{rp.id})</option>))}
                      </select>
                      <button
                        className="btn"
                        onClick={async()=>{
                          try {
                            if (!scenarios.length) { setErr('Create a scenario first'); return; }
                            const scenarioId = (selScenario[a.id] ?? scenarios[0]?.id) as number;
                            const rpId = (selRulepack[a.id] ?? rulepacks[0]?.id) as number;
                            if (!rpId) { setErr('No rulepack available'); return; }
                            const r = await api.evaluations.enqueue(a.id, scenarioId, rpId);
                            setToast({ msg: `Evaluation ${r.id} enqueued` });
                            try { const evals = await api.projects.evaluations.list(id); setEvaluations(evals || []); } catch {}
                          } catch (e:any) { setErr(e.message); }
                        }}
                      >Run</button>
                      <button
                        className="btn"
                        disabled={busyEvalId === a.id}
                        onClick={async()=>{
                          try {
                            if (!scenarios.length) { setErr('Create a scenario first'); return; }
                            const scenarioId = (selScenario[a.id] ?? scenarios[0]?.id) as number;
                            const rpId = (selRulepack[a.id] ?? rulepacks[0]?.id) as number;
                            if (!rpId) { setErr('No rulepack available'); return; }
                            setBusyEvalId(a.id);
                            const r = await api.evaluations.enqueue(a.id, scenarioId, rpId);
                            const done = await pollEvaluation(r.id, 120000, 1500);
                            if (!done) { setErr('Timed out waiting for evaluation'); setBusyEvalId(null); return; }
                            const rep = await api.evaluations.report(done.id);
                            const url = normalizeS3(rep?.presigned_pdf_url || rep?.presigned_html_url);
                            if (url) { window.open(url, '_blank'); }
                            await loadReports();
                            setToast({ msg: `Report generated for eval ${done.id}` });
                          } catch (e:any) { setErr(e.message); }
                          finally { setBusyEvalId(null); }
                        }}
                      >{busyEvalId === a.id ? 'Running…' : 'Run & Report'}</button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
          {tab === 'scenarios' && (
            <>
              <h2>Scenarios</h2>
              <ul>
                {scenarios.map((s) => (
                  <li key={s.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                    <span>{s.name} (#{s.id})</span>
                    <div className="row">
                      <button className="btn btn-outline" onClick={async()=>{
                        try {
                          const data = await api.scenarios.get(s.id);
                          const file = new Blob([JSON.stringify({ id: data.id, project_id: data.project_id, name: data.name, config: data.config }, null, 2)], { type: 'application/json' });
                          const url = URL.createObjectURL(file);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `${(data.name || 'scenario').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')}_${data.id}.json`;
                          document.body.appendChild(a);
                          a.click();
                          a.remove();
                          URL.revokeObjectURL(url);
                        } catch (e:any) { setErr(e.message); }
                      }}>Download</button>
                      <button className="btn btn-danger" onClick={()=>setPendingScenarioDelete(s.id)}>Delete</button>
                    </div>
                  </li>
                ))}
              </ul>
              <h3>New Scenario</h3>
              <form
                onSubmit={async (e) => {
                  e.preventDefault(); setErr(null);
              try {
                let cfg: any = undefined;
                if (newScenConfig.trim()) cfg = JSON.parse(newScenConfig);
                const s = await api.scenarios.create(id, newScenName || 'Scenario', cfg);
                setScenarios((prev) => [...prev, s]);
                setNewScenName(''); setNewScenConfig('');
                setToast({ msg: 'Scenario created' });
              } catch (e:any) { setErr(e.message); }
                }}
                aria-label="Create scenario (project)"
              >
                <label htmlFor="snP">Name</label>
                <input id="snP" value={newScenName} onChange={(e)=>setNewScenName(e.target.value)} required />
                <label htmlFor="scfgP">Config JSON (optional)</label>
                <textarea id="scfgP" rows={4} value={newScenConfig} onChange={(e)=>setNewScenConfig(e.target.value)} placeholder='{"distance_to_control_cm":50}' />
                <div className="space" />
                <button type="submit">Create Scenario</button>
              </form>
            </>
          )}
          {tab === 'reports' && (
            <>
              <h2>Generated Reports</h2>
              <div className="row">
                <button className="btn btn-outline" onClick={() => { void loadReports(); }}>Refresh</button>
              </div>
              <div className="space" />
              {reports.length === 0 && (
                <div className="muted">No reports yet. Generate one from an Evaluation (open an evaluation and click "Generate Report").</div>
              )}
              <ul>
                {reports.map((r) => (
                  <li key={r.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                    <span>#{r.id} — {r.title || 'Report'} {r.created_at ? `(${new Date(r.created_at).toLocaleString()})` : ''}</span>
                    <div className="row">
                      {r.presigned_html_url && <a className="btn btn-outline" href={normalizeS3(r.presigned_html_url)} target="_blank" rel="noreferrer">Open HTML</a>}
                      {r.presigned_pdf_url && <a className="btn" href={normalizeS3(r.presigned_pdf_url)} target="_blank" rel="noreferrer">Open PDF</a>}
                      <button className="btn btn-danger" onClick={async()=>{ try { await api.projects.reports.delete(id, r.id); await loadReports(); setToast({ msg: 'Report deleted' }); } catch(e:any){ setErr(e.message);} }}>Delete</button>
                  </div>
                </li>
              ))}
              </ul>
              <div className="space" />
              <h2>Evaluations</h2>
              <ul>
                {evaluations.map(ev => (
                  <li key={ev.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                    <span>#{ev.id} — {ev.status} {ev.created_at ? `(${new Date(ev.created_at).toLocaleString()})` : ''}</span>
                    <div className="row">
                      <button className="btn" disabled={ev.status !== 'done'} onClick={async()=>{
                        try {
                          const rep = await api.evaluations.report(ev.id);
                          const url = normalizeS3(rep?.presigned_pdf_url || rep?.presigned_html_url);
                          if (url) { window.open(url, '_blank'); await loadReports(); setToast({ msg: 'Report generated' }); }
                          else { setErr('Report generated but URL missing'); }
                        } catch (e:any) { setErr(e.message); }
                      }}>Generate Report</button>
                      <a className="btn btn-outline" href={href({ name: 'evaluation', id: ev.id })}>Open Evaluation</a>
                      <button className="btn btn-danger" onClick={async()=>{ try { await api.evaluations.delete(ev.id); setEvaluations(prev => prev.filter(x => x.id !== ev.id)); setToast({ msg: 'Evaluation deleted' }); } catch(e:any){ setErr(e.message); } }}>Delete</button>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
          {tab === 'users' && (
            <>
              <h2>Users</h2>
              <ul>
                {members.map((u) => (
                  <li key={u.id} style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding: 4 }}>
                    <span>{u.email} (#{u.id})</span>
                    <button className="btn btn-outline" onClick={async()=>{
                      try { await api.projects.members.remove(id, u.id); const mem = await api.projects.members.list(id); setMembers(mem); setToast({ msg: 'User removed' }); }
                      catch (e:any) { setErr(e.message); }
                    }}>Remove</button>
                  </li>
                ))}
              </ul>
              <div className="space" />
              <h3>Add User to Project</h3>
              {allUsers.length > 0 ? (
                <div className="row">
                  <select value={addUserId || ''} onChange={(e)=>setAddUserId(e.target.value ? Number(e.target.value) : '')}>
                    <option value="">-- select user --</option>
                    {allUsers.filter(u => !members.find(m=>m.id===u.id)).map(u => (
                      <option key={u.id} value={u.id}>{u.email} (#{u.id})</option>
                    ))}
                  </select>
                  <button className="btn" onClick={async()=>{
                    if (!addUserId) return;
                    try { await api.projects.members.add(id, Number(addUserId)); const mem = await api.projects.members.list(id); setMembers(mem); setAddUserId(''); setToast({ msg: 'User added' }); }
                    catch (e:any) { setErr(e.message); }
                  }}>Add</button>
                </div>
              ) : (
                <form onSubmit={async (e)=>{ e.preventDefault(); if (!addUserId) return; try { await api.projects.members.add(id, Number(addUserId)); const mem = await api.projects.members.list(id); setMembers(mem); setAddUserId(''); } catch (e:any){ setErr(e.message);} }} aria-label="Add user by ID">
                  <label htmlFor="uid">User ID</label>
                  <input id="uid" type="number" value={addUserId as any} onChange={(e)=>setAddUserId(e.target.value ? Number(e.target.value) : '')} />
                  <div className="space" />
                  <button className="btn" type="submit">Add</button>
                </form>
              )}
            </>
          )}
          {tab === 'edit' && (
            <>
              <h2>Edit Project</h2>
              <form
                onSubmit={async (e) => {
                  e.preventDefault(); setErr(null);
                  try { const p = await api.projects.update(id, name, desc || undefined); setProject(p); setToast({ msg: 'Project updated' }); }
                  catch (e: any) { setErr(e.message); }
                }}
                aria-label="Edit project"
              >
                <label htmlFor="pn">Name</label>
                <input id="pn" value={name} onChange={(e) => setName(e.target.value)} required />
                <label htmlFor="pd">Description</label>
                <input id="pd" value={desc} onChange={(e) => setDesc(e.target.value)} />
                <div className="space" />
                <button type="submit">Save</button>
              </form>
              <div className="space" />
              <h2>Inclusivity Index (trend)</h2>
              <div className="panel" aria-label="Inclusivity Index Trend">
                {/* Stubbed chart */}
                <div className="progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={72} role="progressbar">
                  <div className="bar" style={{ width: '72%' }} />
                </div>
                <div className="muted">Stubbed data (trend coming soon)</div>
              </div>
            </>
          )}
          {tab === 'danger' && (
            <>
              <h2>Danger Zone</h2>
              <div className="panel">
                <button className="btn btn-danger" onClick={() => setConfirmDelete(true)}>Delete Project</button>
              </div>
            </>
          )}
          
        </>
      )}
      {err && <div role="alert" className="muted">{err}</div>}
      <Confirm
        open={confirmDelete}
        title="Delete project?"
        message="This will remove the project and related items."
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          try { await api.projects.delete(id); window.location.hash = href({ name: 'projects' }); }
          catch (e: any) { setErr(e.message); }
          finally { setConfirmDelete(false); }
        }}
      />
      <Confirm
        open={pendingScenarioDelete !== null}
        title="Delete scenario?"
        message="This action cannot be undone."
        onCancel={() => setPendingScenarioDelete(null)}
        onConfirm={async () => {
          if (!pendingScenarioDelete) return;
          try {
            await api.scenarios.delete(pendingScenarioDelete);
            setScenarios(prev => prev.filter(s => s.id !== pendingScenarioDelete));
            setPendingScenarioDelete(null);
            setToast({ msg: 'Scenario deleted' });
          } catch (e:any) {
            setErr(e.message);
            setPendingScenarioDelete(null);
          }
        }}
      />
      {toast && <Toast message={toast.msg} onClose={() => setToast(null)} />}
    </Layout>
  );
}
