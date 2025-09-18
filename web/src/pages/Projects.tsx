import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { href } from '../router';

type Project = { id: number; name: string; description?: string };

export default function ProjectsPage() {
  const [items, setItems] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [err, setErr] = useState<string | null>(null);

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
      <h1>Projects</h1>
      <div className="space" />
      <form onSubmit={onCreate} aria-label="Create project">
        <label htmlFor="pname">Name</label>
        <input id="pname" value={name} onChange={(e) => setName(e.target.value)} required />
        <label htmlFor="pdesc">Description</label>
        <input id="pdesc" value={desc} onChange={(e) => setDesc(e.target.value)} />
        <div className="space" />
        <button type="submit">Create</button>
        {err && <div role="alert" className="muted">{err}</div>}
      </form>
      <div className="space" />
      <ul aria-label="Project list">
        {items.map((p) => (
          <li key={p.id} style={{ padding: 8 }}>
            <a href={href({ name: 'project', id: p.id })}>{p.name}</a>
            {' '}
            <a href={href({ name: 'artifacts', id: p.id })} style={{ marginLeft: 8 }}>Artifacts</a>
          </li>
        ))}
      </ul>
    </Layout>
  );
}
