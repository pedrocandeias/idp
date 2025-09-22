import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type Scenario = { id: number; name: string };

export default function ScenariosPage({ projectId }: { projectId: number }) {
  const [items, setItems] = useState<Scenario[]>([]);
  const [name, setName] = useState('');
  const [config, setConfig] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; undo?: () => void } | null>(null);

  async function load() {
    try {
      const data = await api.scenarios.list(projectId);
      setItems(data);
    } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { void load(); }, [projectId]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      let cfg: any = undefined;
      if (config.trim()) cfg = JSON.parse(config);
      await api.scenarios.create(projectId, name, cfg);
      setName(''); setConfig('');
      await load();
      setToast({ msg: 'Scenario created' });
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <Layout>
      <h1>Scenarios</h1>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create scenario">
        <label htmlFor="sn">Name</label>
        <input id="sn" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="scfg">Config JSON (optional)</label>
        <textarea id="scfg" rows={4} value={config} onChange={(e) => setConfig(e.target.value)} placeholder='{"distance_to_control_cm":50}' />
        <div className="space" />
        <button type="submit">Create</button>
        {err && <div className="muted" role="alert">{err}</div>}
      </form>
      <div className="space" />
      <ul aria-label="Scenario list">
        {items.map((s) => (
          <li key={s.id} style={{ padding: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{s.name} (#{s.id})</span>
            <button aria-label={`Delete scenario ${s.id}`} onClick={() => setPendingDelete(s.id)}>Delete</button>
          </li>
        ))}
      </ul>
      <Confirm
        open={pendingDelete !== null}
        title="Delete scenario?"
        message="This action cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            const s = await api.scenarios.get(pendingDelete);
            await api.scenarios.delete(pendingDelete);
            setPendingDelete(null);
            await load();
            setToast({ msg: 'Scenario deleted', undo: async () => { await api.scenarios.create(projectId, s.name, s.config); await load(); } });
          } catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && <Toast message={toast.msg} actionLabel={toast.undo ? 'Undo' : undefined} onAction={toast.undo} onClose={() => setToast(null)} />}
    </Layout>
  );
}
