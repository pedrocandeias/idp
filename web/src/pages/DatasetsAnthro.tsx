import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type Anthro = { id: number; name: string; source?: string };

export default function DatasetsAnthroPage() {
  const [items, setItems] = useState<Anthro[]>([]);
  const [name, setName] = useState('');
  const [source, setSource] = useState('');
  const [distributions, setDistributions] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; undo?: () => void } | null>(null);

  async function load() {
    try {
      const data = await api.datasets.anthro.list();
      setItems(data);
    } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { void load(); }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      let dist: any = undefined;
      if (distributions.trim()) dist = JSON.parse(distributions);
      await api.datasets.anthro.create(name, source || undefined, undefined, dist);
      setName(''); setSource(''); setDistributions('');
      await load();
      setToast({ msg: 'Dataset created' });
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <Layout>
      <h1>Datasets: Anthropometrics</h1>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create anthropometric dataset">
        <label htmlFor="an">Name</label>
        <input id="an" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="as">Source</label>
        <input id="as" value={source} onChange={(e) => setSource(e.target.value)} />
        <label htmlFor="ad">Distributions JSON (optional)</label>
        <textarea id="ad" rows={4} value={distributions} onChange={(e) => setDistributions(e.target.value)} placeholder='{"height_cm":{"p50":170}}' />
        <div className="space" />
        <button type="submit">Create</button>
        {err && <div className="muted" role="alert">{err}</div>}
      </form>
      <div className="space" />
      <table className="table" role="table" aria-label="Anthropometric datasets">
        <thead><tr><th>ID</th><th>Name</th><th>Source</th><th>Actions</th></tr></thead>
        <tbody>
          {items.map((x) => (
            <tr key={x.id}>
              <td>{x.id}</td><td>{x.name}</td><td>{x.source || ''}</td>
              <td><button className="btn btn-danger" onClick={() => setPendingDelete(x.id)}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <Confirm
        open={pendingDelete !== null}
        title="Delete dataset?"
        message="This action cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            // Fetch details for undo
            const ds = await api.datasets.anthro.get(pendingDelete);
            await api.datasets.anthro.delete(pendingDelete);
            setPendingDelete(null);
            await load();
            setToast({
              msg: 'Dataset deleted',
              undo: async () => { await api.datasets.anthro.create(ds.name, ds.source, ds.schema, ds.distributions); await load(); },
            });
          } catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && (
        <Toast message={toast.msg} actionLabel={toast.undo ? 'Undo' : undefined} onAction={toast.undo} onClose={() => setToast(null)} />
      )}
    </Layout>
  );
}
