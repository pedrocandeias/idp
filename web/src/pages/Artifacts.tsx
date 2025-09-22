import React, { useState, DragEvent, useEffect } from 'react';
import Layout from '../components/Layout';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';
import { api, normalizeS3 } from '../lib/api';
import { href } from '../router';

export default function ArtifactsPage({ projectId }: { projectId: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [params, setParams] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<any>(null);
  const [scenarioId, setScenarioId] = useState<number | ''>('');
  const [rulepackId, setRulepackId] = useState<number | ''>('');
  const [scenarios, setScenarios] = useState<Array<{ id: number; name: string }>>([]);
  const [rulepacks, setRulepacks] = useState<Array<{ id: number; name: string; version?: string }>>([]);
  const [newScenName, setNewScenName] = useState('');
  const [newScenConfig, setNewScenConfig] = useState('');
  const [newRpName, setNewRpName] = useState('');
  const [newRpVersion, setNewRpVersion] = useState('1.0.0');
  const [newRpRules, setNewRpRules] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [toast, setToast] = useState<{ msg: string } | null>(null);

  function onDrop(e: DragEvent) {
    e.preventDefault();
    const items = e.dataTransfer.files;
    if (items.length > 0) {
      const f = items[0];
      setFile(f);
      setName(f.name);
    }
  }
  function onDragOver(e: DragEvent) { e.preventDefault(); }

  async function loadLists() {
    try {
      const [scs, rps] = await Promise.all([
        api.scenarios.list(projectId),
        api.rulepacks.list(),
      ]);
      setScenarios(scs);
      setRulepacks(rps);
      if (!scenarioId && scs.length) setScenarioId(scs[0].id);
      if (!rulepackId && rps.length) setRulepackId(rps[0].id);
    } catch (e: any) {
      setStatus(e.message || 'Failed to load lists');
    }
  }

  useEffect(() => { void loadLists(); }, [projectId]);

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setStatus('Uploading...');
    try {
      const res = await api.artifacts.upload(projectId, file, params ?? undefined, name || file.name);
      const normalized = { ...res, presigned_url: normalizeS3(res.presigned_url) };
      setArtifact(normalized);
      if (normalized.presigned_url) {
        sessionStorage.setItem(`artifact_url_${res.id}`, normalized.presigned_url as string);
      }
      setStatus('Uploaded.');
    } catch (e: any) {
      setStatus(e.message);
    }
  }

  async function onLaunchEvaluation(e: React.FormEvent) {
    e.preventDefault();
    if (!artifact || !scenarioId || !rulepackId) return;
    setStatus('Enqueuing evaluation...');
    try {
      const res = await api.evaluations.enqueue(artifact.id, Number(scenarioId), Number(rulepackId));
      window.location.hash = href({ name: 'evaluation', id: res.id });
    } catch (e: any) {
      setStatus(e.message);
    }
  }

  async function onCreateScenario(e: React.FormEvent) {
    e.preventDefault();
    try {
      let cfg: any = undefined;
      if (newScenConfig.trim()) cfg = JSON.parse(newScenConfig);
      const s = await api.scenarios.create(projectId, newScenName || 'Scenario', cfg);
      setScenarios((prev) => [...prev, s]);
      setScenarioId(s.id);
      setNewScenName('');
      setNewScenConfig('');
      setStatus('Scenario created');
    } catch (e: any) {
      setStatus(e.message || 'Failed to create scenario');
    }
  }

  async function onCreateRulepack(e: React.FormEvent) {
    e.preventDefault();
    try {
      let rules: any = undefined;
      if (newRpRules.trim()) rules = JSON.parse(newRpRules);
      const rp = await api.rulepacks.create(newRpName || 'RulePack', newRpVersion || '1.0.0', rules);
      setRulepacks((prev) => [...prev, rp]);
      setRulepackId(rp.id);
      setNewRpName('');
      setNewRpVersion('1.0.0');
      setNewRpRules('');
      setStatus('RulePack created');
    } catch (e: any) {
      setStatus(e.message || 'Failed to create rulepack');
    }
  }

  return (
    <Layout>
      <h1>Artifacts</h1>
      <div className="space" />
      <div onDrop={onDrop} onDragOver={onDragOver} role="region" aria-label="Drop glTF or STEP file" className="panel" style={{ textAlign: 'center' }}>
        <p>Drag & drop glTF/GLB/STEP here</p>
        <input type="file" aria-label="Choose 3D file" accept=".gltf,.glb,.stp,.step" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <div className="space" />
        <label htmlFor="pjson">Parametric JSON (optional)</label>
        <input id="pjson" type="file" accept="application/json" onChange={(e) => setParams(e.target.files?.[0] ?? null)} />
        <div className="space" />
        <label htmlFor="name">Name</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="space" />
        <button onClick={onUpload as any} aria-label="Upload artifact">Upload</button>
      </div>
      <div className="space" />
      {artifact && (
        <div className="panel">
          <h2>Launch Evaluation</h2>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div className="muted">Current artifact ID: {artifact?.id}</div>
            <button className="btn btn-danger" onClick={() => setConfirmDelete(true)}>Delete Artifact</button>
          </div>
          <div className="space" />
          <div className="row">
            <div style={{ flex: 1, minWidth: 280 }}>
              <h3>Scenario</h3>
              <label htmlFor="scSel">Select</label>
              <select id="scSel" value={scenarioId || ''} onChange={(e) => setScenarioId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">-- choose --</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} (#{s.id})</option>
                ))}
              </select>
              <div className="space" />
              <form onSubmit={onCreateScenario} aria-label="Create scenario">
                <label htmlFor="nsn">New name</label>
                <input id="nsn" value={newScenName} onChange={(e) => setNewScenName(e.target.value)} placeholder="My Scenario" />
                <label htmlFor="nscfg">Config JSON (optional)</label>
                <textarea id="nscfg" value={newScenConfig} onChange={(e) => setNewScenConfig(e.target.value)} rows={4} placeholder='{"distance_to_control_cm":50}' />
                <div className="space" />
                <button type="submit">Create Scenario</button>
              </form>
            </div>
            <div style={{ width: 16 }} />
            <div style={{ flex: 1, minWidth: 280 }}>
              <h3>RulePack</h3>
              <label htmlFor="rpSel">Select</label>
              <select id="rpSel" value={rulepackId || ''} onChange={(e) => setRulepackId(e.target.value ? Number(e.target.value) : '')}>
                <option value="">-- choose --</option>
                {rulepacks.map((rp) => (
                  <option key={rp.id} value={rp.id}>{rp.name}{rp.version ? ` v${rp.version}` : ''} (#{rp.id})</option>
                ))}
              </select>
              <div className="space" />
              <form onSubmit={onCreateRulepack} aria-label="Create rulepack">
                <label htmlFor="nrn">New name</label>
                <input id="nrn" value={newRpName} onChange={(e) => setNewRpName(e.target.value)} placeholder="My Rules" />
                <label htmlFor="nrv">Version</label>
                <input id="nrv" value={newRpVersion} onChange={(e) => setNewRpVersion(e.target.value)} placeholder="1.0.0" />
                <label htmlFor="nrr">Rules JSON (optional)</label>
                <textarea id="nrr" value={newRpRules} onChange={(e) => setNewRpRules(e.target.value)} rows={4} placeholder='{"example":true}' />
                <div className="space" />
                <button type="submit">Create RulePack</button>
              </form>
            </div>
          </div>
          <div className="space" />
          <form onSubmit={onLaunchEvaluation} className="row" aria-label="Launch evaluation">
            <button type="submit" aria-label="Enqueue evaluation" disabled={!scenarioId || !rulepackId}>Enqueue</button>
          </form>
        </div>
      )}
      <Confirm
        open={confirmDelete}
        title="Delete artifact?"
        message="You will need to upload again."
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          try {
            if (artifact?.id) {
              await api.artifacts.delete(projectId, artifact.id);
              sessionStorage.removeItem(`artifact_url_${artifact.id}`);
            }
            setArtifact(null);
            setConfirmDelete(false);
            setToast({ msg: 'Artifact deleted' });
          } catch (e: any) {
            setStatus(e.message);
            setConfirmDelete(false);
          }
        }}
      />
      {toast && <Toast message={toast.msg} onClose={() => setToast(null)} />}
      {status && <div className="muted" role="status">{status}</div>}
    </Layout>
  );
}
