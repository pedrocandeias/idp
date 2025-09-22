import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { href } from '../router';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type Project = { id: number; name: string; description?: string };

export default function ProjectsPage() {
  const [items, setItems] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; undo?: () => void } | null>(null);

  async function load() {
    try {
      const data = await api.projects.list();
      setItems(data);
    } catch (e: any) {
      setErr(e.message);
    }
  }
  useEffect(() => { void load(); }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await api.projects.create(name, desc);
      setName(''); setDesc('');
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Layout>
      <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>Projects</h1>
        <button
          aria-label="Run demo"
          onClick={async () => {
            setErr(null);
            try {
              const res = await api.demo.seed();
              await load();
              if (res?.evaluation_id) {
                window.location.hash = href({ name: 'evaluation', id: res.evaluation_id });
              }
            } catch (e: any) {
              setErr(e.message || 'Demo failed');
            }
          }}
        >Run Demo</button>
      </div>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create project">
        <label htmlFor="pname">Name</label>
        <input id="pname" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="pdesc">Description</label>
        <input id="pdesc" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <div className="space" />
        <button type="submit" className="btn btn-primary">Create</button>
        {err && <div role="alert" className="muted">{err}</div>}
      </form>
      <div className="space" />
      <ul aria-label="Project list">
        {items.map((p) => (
          <li key={p.id} style={{ padding: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>
              <a href={href({ name: 'project', id: p.id })}>{p.name}</a>
              {' '}
              <a href={href({ name: 'artifacts', id: p.id })} style={{ marginLeft: 8 }}>Artifacts</a>
            </span>
            <button className="btn btn-danger" aria-label={`Delete project ${p.id}`} onClick={() => setPendingDelete(p.id)}>Delete</button>
          </li>
        ))}
      </ul>
      <Confirm
        open={pendingDelete !== null}
        title="Delete project?"
        message="This will remove the project and related items."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            // fetch details for undo
            const proj = await api.projects.get(pendingDelete);
            await api.projects.delete(pendingDelete);
            setPendingDelete(null);
            await load();
            setToast({
              msg: 'Project deleted',
              undo: async () => { await api.projects.create(proj.name, proj.description); await load(); },
            });
          }
          catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && (
        <Toast message={toast.msg} actionLabel={toast.undo ? 'Undo' : undefined} onAction={toast.undo} onClose={() => setToast(null)} />
      )}
    </Layout>
  );
}
