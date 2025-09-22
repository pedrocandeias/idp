import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api, normalizeS3 } from '../lib/api';
import ModelViewer from '../components/ModelViewer';
import { href } from '../router';

export default function EvaluationDetailPage({ id }: { id: number }) {
  const [data, setData] = useState<any | null>(null);
  const [artifact, setArtifact] = useState<any | null>(null);
  const [convBusy, setConvBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showReach, setShowReach] = useState(true);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [busyReport, setBusyReport] = useState(false);
  const [busyRefresh, setBusyRefresh] = useState(false);

  async function load() {
    try {
      const d = await api.evaluations.get(id);
      setData(d);
      const aid = d?.metrics?.artifact_id;
      if (aid) {
        const u = sessionStorage.getItem(`artifact_url_${aid}`);
        if (u) setArtifact({ presigned_url: normalizeS3(u) });
        else {
          try {
            const art = await api.artifacts.get(aid);
            if (art) setArtifact({ ...art, presigned_url: normalizeS3(art.presigned_url) });
          } catch {}
        }
      }
    } catch (e: any) {
      setErr(e.message);
    }
  }
  useEffect(() => { void load(); }, [id]);
  useEffect(() => {
    const saved = sessionStorage.getItem(`report_url_${id}`);
    if (saved) setReportUrl(normalizeS3(saved));
  }, [id]);

  async function onRecompute() {
    if (!data) return;
    const { artifact_id, rulepack_id } = data.metrics || {};
    const scenario_id = data.metrics?.scenario_id || data?.scenario_id || null;
    if (!artifact_id || !rulepack_id || !scenario_id) { setErr('Missing ids to recompute'); return; }
    const r = await api.evaluations.enqueue(artifact_id, scenario_id, rulepack_id);
    window.location.hash = href({ name: 'evaluation', id: r.id });
  }

  async function onReport() {
    if (!data) return;
    // Refresh status just before generating
    try { await load(); } catch {}
    if ((data?.status ?? 'pending') !== 'done') { setErr('Evaluation not complete yet'); return; }
    try {
      setBusyReport(true);
      const rep = await api.evaluations.report(id);
      const url = normalizeS3(rep?.presigned_pdf_url || rep?.presigned_html_url);
      if (url) {
        setReportUrl(url);
        sessionStorage.setItem(`report_url_${id}`, url);
        window.open(url, '_blank');
      } else {
        setErr('Report generated but URL missing');
      }
    } catch (e: any) {
      setErr(e.message || 'Report failed');
    } finally {
      setBusyReport(false);
    }
  }
  async function onRefresh() {
    try { setBusyRefresh(true); await load(); }
    finally { setBusyRefresh(false); }
  }

  const rules: Array<any> = data?.results?.rules || [];
  const index = data?.inclusivity_index || { score: 0, components: { reach: false, strength: false, visual: false } };

  return (
    <Layout>
      {!data ? <div>Loading...</div> : (
        <>
          <h1>Evaluation #{id}</h1>
          <div className="row" role="toolbar" aria-label="Viewer controls">
            <button onClick={() => setShowReach((v) => !v)} aria-pressed={showReach} aria-label="Toggle reach envelope">Toggle Reach</button>
            <button onClick={onRecompute} aria-label="Recompute evaluation">Recompute</button>
            <button onClick={onReport} aria-label="Generate report" disabled={busyReport || data?.status !== 'done'}>
              {busyReport ? 'Generating…' : 'Generate Report'}
            </button>
            <button onClick={onRefresh} aria-label="Refresh" disabled={busyRefresh}>{busyRefresh ? 'Refreshing…' : 'Refresh'}</button>
          </div>
          <div className="muted">Status: {data?.status || 'unknown'}</div>
          {reportUrl && (
            <div className="space" />
          )}
          {reportUrl && (
            <div className="panel">
              <strong>Last report:</strong>
              {' '}
              <a href={reportUrl} target="_blank" rel="noreferrer">Open report</a>
            </div>
          )}
          <div className="space" />
          {artifact?.type && (artifact.type === 'gltf' || artifact.type === 'glb') ? (
            <ModelViewer url={artifact?.presigned_url} showReach={showReach} />
          ) : (
            <div className="panel">
              <div className="muted">This artifact is type "{artifact?.type || 'unknown'}". The 3D viewer supports glTF/GLB.</div>
              <div className="space" />
              <button className="btn" disabled={convBusy} onClick={async()=>{
                try {
                  setConvBusy(true);
                  // Request server-side conversion
                  const aid = data?.metrics?.artifact_id;
                  if (!aid) { setConvBusy(false); return; }
                  await api.artifacts.convert(aid);
                  // Poll the artifact until type becomes gltf and URL is ready
                  const deadline = Date.now() + 60000;
                  while (Date.now() < deadline) {
                    const art = await api.artifacts.get(aid);
                    if (art?.type && (art.type === 'gltf' || art.type === 'glb') && art.presigned_url) {
                      setArtifact({ ...art, presigned_url: normalizeS3(art.presigned_url) });
                      break;
                    }
                    await new Promise(r => setTimeout(r, 1500));
                  }
                } catch (e:any) { setErr(e.message); }
                finally { setConvBusy(false); }
              }}>{convBusy ? 'Converting…' : 'Convert to glTF'}</button>
            </div>
          )}
          <div className="space" />
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <h2>Inclusivity Index</h2>
              <div className="progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((index.score||0)*100)} role="progressbar">
                <div className="bar" style={{ width: `${Math.round((index.score||0)*100)}%` }} />
              </div>
              <div className="muted">Reach {index.components?.reach ? '✓' : '✗'} • Strength {index.components?.strength ? '✓' : '✗'} • Visual {index.components?.visual ? '✓' : '✗'}</div>
              {data?.results && (
                <div className="muted">Distance: {data.results.reach?.distance_cm ?? '—'} cm • Required force: {data.results.strength?.required_force_N ?? '—'} N • Contrast: {data.results.visual?.contrast_ratio?.toFixed?.(2) ?? data.results.visual?.contrast_ratio ?? '—'}</div>
              )}
            </div>
            <div style={{ flex: 2 }}>
              <h2>Rule Breakdown</h2>
              <table className="table" role="table" aria-label="Rule breakdown">
                <thead><tr><th>Rule</th><th>Outcome</th><th>Severity</th></tr></thead>
                <tbody>
                  {rules.map((r, i) => (
                    <tr key={i}><td>{r.id}</td><td>{r.passed ? 'PASS' : 'FAIL'}</td><td>{r.severity}</td></tr>
                  ))}
                </tbody>
              </table>
              {rules.length === 0 && (
                <div className="muted">No rule breakdown available. Either the rulepack has no rules, or the evaluation has not completed. Use Refresh to update.</div>
              )}
            </div>
          </div>
        </>
      )}
      {err && <div role="alert" className="muted">{err}</div>}
    </Layout>
  );
}
