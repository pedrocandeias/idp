export type Route =
  | { name: 'login' }
  | { name: 'projects' }
  | { name: 'project'; id: number }
  | { name: 'artifacts'; id: number }
  | { name: 'evaluation'; id: number };

export function parseRoute(hash: string): Route {
  const h = hash.replace(/^#/, '') || '/login';
  const parts = h.split('/').filter(Boolean);
  if (parts.length === 0) return { name: 'login' };
  if (parts[0] === 'login') return { name: 'login' };
  if (parts[0] === 'projects') {
    if (parts.length === 1) return { name: 'projects' };
    const id = Number(parts[1]);
    if (parts.length === 2) return { name: 'project', id };
    if (parts[2] === 'artifacts') return { name: 'artifacts', id };
  }
  if (parts[0] === 'evaluations' && parts[1]) return { name: 'evaluation', id: Number(parts[1]) };
  return { name: 'login' };
}

export function href(to: Route): string {
  if (to.name === 'login') return '#/login';
  if (to.name === 'projects') return '#/projects';
  if (to.name === 'project') return `#/projects/${to.id}`;
  if (to.name === 'artifacts') return `#/projects/${to.id}/artifacts`;
  if (to.name === 'evaluation') return `#/evaluations/${to.id}`;
  return '#/login';
}
