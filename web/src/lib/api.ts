// Prefer same-origin with Vite dev proxy; override via VITE_API_URL when needed
const BASE = (import.meta.env as any).VITE_API_URL ?? '';
const PUBLIC_S3 = (import.meta.env as any).VITE_S3_PUBLIC_ENDPOINT ?? 'http://localhost:9000';

export function normalizeS3(url: string | undefined | null): string | undefined {
  if (!url) return url as any;
  try {
    const u = new URL(url);
    if (u.hostname === 'minio') {
      const pub = new URL(PUBLIC_S3);
      u.protocol = pub.protocol;
      u.host = pub.host; // includes hostname:port
      return u.toString();
    }
  } catch {
    // ignore
  }
  return url;
}

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
  auth: {
    register: (email: string, password: string, org_id?: number) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify(org_id ? { email, password, org_id } : { email, password }),
      }),
  },
  projects: {
    list: () => request('/api/v1/projects'),
    create: (name: string, description?: string) =>
      request('/api/v1/projects', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
      }),
    get: (id: number) => request(`/api/v1/projects/${id}`),
    update: (id: number, name: string, description?: string) =>
      request(`/api/v1/projects/${id}` , {
        method: 'PATCH',
        body: JSON.stringify({ name, description }),
      }),
    delete: (id: number) => request(`/api/v1/projects/${id}`, { method: 'DELETE' }),
    members: {
      list: (projectId: number) => request(`/api/v1/projects/${projectId}/members`),
      add: (projectId: number, user_id: number) => request(`/api/v1/projects/${projectId}/members`, { method: 'POST', body: JSON.stringify({ user_id }) }),
      remove: (projectId: number, user_id: number) => request(`/api/v1/projects/${projectId}/members/${user_id}`, { method: 'DELETE' }),
    },
    reports: {
      list: (projectId: number) => request(`/api/v1/projects/${projectId}/reports`),
      delete: (projectId: number, reportId: number) => request(`/api/v1/projects/${projectId}/reports/${reportId}`, { method: 'DELETE' }),
    },
    evaluations: {
      list: (projectId: number) => request(`/api/v1/projects/${projectId}/evaluations`),
    },
  },
  artifacts: {
    upload: async (projectId: number, file: File, paramsFile?: File, name?: string, type?: string) => {
      const fd = new FormData();
      fd.append('file', file);
      if (paramsFile) fd.append('params', paramsFile);
      if (name) fd.append('name', name);
      if (type) fd.append('type', type);
      const token = getToken();
      const headers: Record<string, string> = { 'Accept': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${BASE}/api/v1/projects/${projectId}/artifacts`, {
        method: 'POST',
        body: fd,
        headers,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
    delete: (projectId: number, id: number) => request(`/api/v1/projects/${projectId}/artifacts/${id}`, { method: 'DELETE' }),
    list: (projectId: number) => request(`/api/v1/projects/${projectId}/artifacts`),
    get: (id: number) => request(`/api/v1/artifacts/${id}`),
    convert: (id: number) => request(`/api/v1/artifacts/${id}/convert`, { method: 'POST' }),
  },
  evaluations: {
    enqueue: (artifact_id: number, scenario_id: number, rulepack_id: number, opts?: { debug?: boolean; webhook_url?: string }) =>
      request('/api/v1/evaluations', { method: 'POST', body: JSON.stringify({ artifact_id, scenario_id, rulepack_id, debug: opts?.debug ?? false, webhook_url: opts?.webhook_url }) }),
    get: (id: number) => request(`/api/v1/evaluations/${id}`),
    report: (id: number) => request(`/api/v1/evaluations/${id}/report`, { method: 'POST' }),
    delete: (id: number) => request(`/api/v1/evaluations/${id}`, { method: 'DELETE' }),
  },
  demo: {
    seed: () => request('/api/v1/demo/seed', { method: 'POST' }),
  },
  scenarios: {
    list: (projectId?: number) => request(`/api/v1/scenarios${projectId ? `?project_id=${projectId}` : ''}`),
    get: (id: number) => request(`/api/v1/scenarios/${id}`),
    create: (project_id: number, name: string, config?: any) =>
      request('/api/v1/scenarios', {
        method: 'POST',
        body: JSON.stringify({ project_id, name, config }),
      }),
    delete: (id: number) => request(`/api/v1/scenarios/${id}`, { method: 'DELETE' }),
  },
  rulepacks: {
    list: () => request('/api/v1/rulepacks'),
    get: (id: number) => request(`/api/v1/rulepacks/${id}`),
    create: (name: string, version: string, rules?: any) =>
      request('/api/v1/rulepacks', {
        method: 'POST',
        body: JSON.stringify({ name, version, rules }),
      }),
    delete: (id: number) => request(`/api/v1/rulepacks/${id}`, { method: 'DELETE' }),
  },
  datasets: {
    anthro: {
      list: () => request('/api/v1/datasets/anthropometrics'),
      get: (id: number) => request(`/api/v1/datasets/anthropometrics/${id}`),
      delete: (id: number) => request(`/api/v1/datasets/anthropometrics/${id}`, { method: 'DELETE' }),
      create: (name: string, source?: string, schema?: any, distributions?: any) =>
        request('/api/v1/datasets/anthropometrics', {
          method: 'POST',
          body: JSON.stringify({ name, source, schema, distributions }),
        }),
    },
    abilities: {
      list: () => request('/api/v1/datasets/abilities'),
      get: (id: number) => request(`/api/v1/datasets/abilities/${id}`),
      delete: (id: number) => request(`/api/v1/datasets/abilities/${id}`, { method: 'DELETE' }),
      create: (name: string, data?: any) =>
        request('/api/v1/datasets/abilities', {
          method: 'POST',
          body: JSON.stringify({ name, data, org_id: 0 }),
        }),
    },
  },
  users: {
    me: () => request('/api/v1/me'),
    list: () => request('/api/v1/users'),
    setRoles: (id: number, roles: string[]) =>
      request(`/api/v1/users/${id}/roles`, { method: 'PATCH', body: JSON.stringify({ roles }) }),
    setPassword: (id: number, password: string) =>
      request(`/api/v1/users/${id}/password`, { method: 'PATCH', body: JSON.stringify({ password }) }),
    delete: (id: number) => request(`/api/v1/users/${id}`, { method: 'DELETE' }),
  }
};
