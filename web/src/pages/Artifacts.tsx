import React, { useState, DragEvent } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { href } from '../router';

export default function ArtifactsPage({ projectId }: { projectId: number }) {
  const [file, setFile] = useState<File | null>(null);
  const [params, setParams] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [artifact, setArtifact] = useState<any>(null);
  const [scenarioId, setScenarioId] = useState<number | ''>('');
  const [rulepackId, setRulepackId] = useState<number | ''>('');

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

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setStatus('Uploading...');
    try {
      const res = await api.artifacts.upload(projectId, file, params ?? undefined, name || file.name);
      setArtifact(res);
      if (res.presigned_url) {
        sessionStorage.setItem(`artifact_url_${res.id}`, res.presigned_url as string);
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
          <form onSubmit={onLaunchEvaluation} className="row" aria-label="Launch evaluation">
            <label htmlFor="sc">Scenario ID</label>
            <input id="sc" value={scenarioId} onChange={(e) => setScenarioId(e.target.value ? Number(e.target.value) : '')} />
            <label htmlFor="rp">RulePack ID</label>
            <input id="rp" value={rulepackId} onChange={(e) => setRulepackId(e.target.value ? Number(e.target.value) : '')} />
            <button type="submit" aria-label="Enqueue evaluation">Enqueue</button>
          </form>
        </div>
      )}
      {status && <div className="muted" role="status">{status}</div>}
    </Layout>
  );
}
