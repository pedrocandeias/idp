const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

import { getToken, setToken } from './auth';

type Opts = RequestInit & { auth?: boolean };

async function request(path: string, opts: Opts = {}) {
  const headers = new Headers(opts.headers || {});
  headers.set('Accept', 'application/json');
  if (!(opts.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  if (opts.auth !== false) {
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  const res = await fetch(`${BASE}${path}`, { ...opts, headers, credentials: 'include' });
  if (res.status === 401) {
    setToken(null);
    window.location.hash = '#/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || res.statusText);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

export const api = {
  async login(email: string, password: string): Promise<string> {
    const form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    const res = await fetch(`${BASE}/auth/token`, {
      method: 'POST',
      body: form,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    if (!res.ok) throw new Error('Login failed');
    const data = await res.json();
    return data.access_token as string;
  },
  projects: {
    list: () => request('/api/v1/projects'),
    create: (name: string, description?: string) =>
      request('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
      }),
    get: (id: number) => request(`/api/v1/projects/${id}`),
  },
  artifacts: {
    upload: async (projectId: number, file: File, paramsFile?: File, name?: string, type?: string) => {
      const fd = new FormData();
      fd.append('file', file);
      if (paramsFile) fd.append('params', paramsFile);
      if (name) fd.append('name', name);
      if (type) fd.append('type', type);
      const res = await fetch(`${BASE}/api/v1/projects/${projectId}/artifacts`, {
        method: 'POST',
        body: fd,
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
  },
  evaluations: {
    enqueue: (artifact_id: number, scenario_id: number, rulepack_id: number) =>
      request('/api/v1/evaluations', { method: 'POST', body: JSON.stringify({ artifact_id, scenario_id, rulepack_id }) }),
    get: (id: number) => request(`/api/v1/evaluations/${id}`),
  }
};
