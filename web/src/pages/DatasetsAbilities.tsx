import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type Ability = { id: number; name: string };

export default function DatasetsAbilitiesPage() {
  const [items, setItems] = useState<Ability[]>([]);
  const [name, setName] = useState('');
  const [data, setData] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; undo?: () => void } | null>(null);

  async function load() {
    try {
      const data = await api.datasets.abilities.list();
      setItems(data);
    } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { void load(); }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      let parsed: any = undefined;
      if (data.trim()) parsed = JSON.parse(data);
      await api.datasets.abilities.create(name, parsed);
      setName(''); setData('');
      await load();
      setToast({ msg: 'Ability profile created' });
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <Layout>
      <h1>Datasets: Abilities</h1>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create ability profile">
        <label htmlFor="bn">Name</label>
        <input id="bn" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="bd">Data JSON (optional)</label>
        <textarea id="bd" rows={4} value={data} onChange={(e) => setData(e.target.value)} placeholder='{"strength_N":30}' />
        <div className="space" />
        <button type="submit">Create</button>
        {err && <div className="muted" role="alert">{err}</div>}
      </form>
      <div className="space" />
      <table className="table" role="table" aria-label="Ability profiles">
        <thead><tr><th>ID</th><th>Name</th><th>Actions</th></tr></thead>
        <tbody>
          {items.map((x) => (
            <tr key={x.id}>
              <td>{x.id}</td><td>{x.name}</td>
              <td><button className="btn btn-danger" onClick={() => setPendingDelete(x.id)}>Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <Confirm
        open={pendingDelete !== null}
        title="Delete ability profile?"
        message="This action cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            const item = await api.datasets.abilities.get(pendingDelete);
            await api.datasets.abilities.delete(pendingDelete);
            setPendingDelete(null);
            await load();
            setToast({
              msg: 'Ability profile deleted',
              undo: async () => { await api.datasets.abilities.create(item.name, item.data); await load(); },
            });
          } catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && <Toast message={toast.msg} actionLabel={toast.undo ? 'Undo' : undefined} onAction={toast.undo} onClose={() => setToast(null)} />}
    </Layout>
  );
}
