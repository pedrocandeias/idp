import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import Confirm from '../components/Confirm';
import Toast from '../components/Toast';

type RulePack = { id: number; name: string; version?: string };

export default function RulepacksPage() {
  const [items, setItems] = useState<RulePack[]>([]);
  const [name, setName] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [rules, setRules] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);
  const [toast, setToast] = useState<{ msg: string; undo?: () => void } | null>(null);

  async function load() {
    try {
      const data = await api.rulepacks.list();
      setItems(data);
    } catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { void load(); }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      let parsed: any = undefined;
      if (rules.trim()) parsed = JSON.parse(rules);
      await api.rulepacks.create(name, version, parsed);
      setName(''); setVersion('1.0.0'); setRules('');
      await load();
      setToast({ msg: 'Rulepack created' });
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <Layout>
      <h1>RulePacks</h1>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create rulepack">
        <label htmlFor="rpn">Name</label>
        <input id="rpn" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="rpv">Version</label>
        <input id="rpv" value={version} onChange={(e) => setVersion(e.target.value)} />
        <label htmlFor="rpr">Rules JSON (optional)</label>
        <textarea id="rpr" rows={4} value={rules} onChange={(e) => setRules(e.target.value)} placeholder='{"example":true}' />
        <div className="space" />
        <button type="submit">Create</button>
        {err && <div className="muted" role="alert">{err}</div>}
      </form>
      <div className="space" />
      <table className="table" role="table" aria-label="Rulepacks list">
        <thead><tr><th>ID</th><th>Name</th><th>Version</th><th>Actions</th></tr></thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td><td>{r.name}</td><td>{r.version || ''}</td>
              <td>
                <button aria-label={`Delete rulepack ${r.id}`} onClick={() => setPendingDelete(r.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Confirm
        open={pendingDelete !== null}
        title="Delete rulepack?"
        message="This action cannot be undone."
        onCancel={() => setPendingDelete(null)}
        onConfirm={async () => {
          if (!pendingDelete) return;
          try {
            const rp = await api.rulepacks.get(pendingDelete);
            await api.rulepacks.delete(pendingDelete);
            setPendingDelete(null);
            await load();
            setToast({ msg: 'Rulepack deleted', undo: async () => { await api.rulepacks.create(rp.name, rp.version || '1.0.0', rp.rules); await load(); } });
          } catch (e: any) { setErr(e.message); setPendingDelete(null); }
        }}
      />
      {toast && <Toast message={toast.msg} actionLabel={toast.undo ? 'Undo' : undefined} onAction={toast.undo} onClose={() => setToast(null)} />}
    </Layout>
  );
}
