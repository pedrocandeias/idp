import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';

type Project = { id: number; name: string; description?: string };

export default function ProjectDetailPage({ id }: { id: number }) {
  const [project, setProject] = useState<Project | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    (async () => {
      try {
        const p = await api.projects.get(id);
        setProject(p);
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
      {err && <div role="alert" className="muted">{err}</div>}
    </Layout>
  );
}

