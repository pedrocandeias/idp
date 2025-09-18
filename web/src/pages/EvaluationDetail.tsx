import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import ModelViewer from '../components/ModelViewer';
import { href } from '../router';

export default function EvaluationDetailPage({ id }: { id: number }) {
  const [data, setData] = useState<any | null>(null);
  const [artifact, setArtifact] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showReach, setShowReach] = useState(true);

  async function load() {
    try {
      const d = await api.evaluations.get(id);
      setData(d);
      const aid = d?.metrics?.artifact_id;
      if (aid) {
        const u = sessionStorage.getItem(`artifact_url_${aid}`);
        if (u) setArtifact({ presigned_url: u });
      }
    } catch (e: any) {
      setErr(e.message);
    }
  }
  useEffect(() => { void load(); }, [id]);

  async function onRecompute() {
    if (!data) return;
    const { artifact_id, rulepack_id } = data.metrics || {};
    const scenario_id = data.metrics?.scenario_id || data?.scenario_id || null;
    if (!artifact_id || !rulepack_id || !scenario_id) { setErr('Missing ids to recompute'); return; }
    const r = await api.evaluations.enqueue(artifact_id, scenario_id, rulepack_id);
    window.location.hash = href({ name: 'evaluation', id: r.id });
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
          </div>
          <div className="space" />
          <ModelViewer url={artifact?.presigned_url} showReach={showReach} />
          <div className="space" />
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <h2>Inclusivity Index</h2>
              <div className="progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round((index.score||0)*100)} role="progressbar">
                <div className="bar" style={{ width: `${Math.round((index.score||0)*100)}%` }} />
              </div>
              <div className="muted">Reach {index.components?.reach ? '✓' : '✗'} • Strength {index.components?.strength ? '✓' : '✗'} • Visual {index.components?.visual ? '✓' : '✗'}</div>
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
            </div>
          </div>
        </>
      )}
      {err && <div role="alert" className="muted">{err}</div>}
    </Layout>
  );
}
