export type Route =
  | { name: 'login' }
  | { name: 'projects' }
  | { name: 'project'; id: number }
  | { name: 'artifacts'; id: number }
  | { name: 'evaluation'; id: number }
  | { name: 'project_scenarios'; id: number }
  | { name: 'rulepacks' }
  | { name: 'datasets_anthro' }
  | { name: 'datasets_abilities' }
  | { name: 'admin' };

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
    if (parts[2] === 'scenarios') return { name: 'project_scenarios', id };
  }
  if (parts[0] === 'evaluations' && parts[1]) return { name: 'evaluation', id: Number(parts[1]) };
  if (parts[0] === 'rulepacks') return { name: 'rulepacks' };
  if (parts[0] === 'datasets' && parts[1] === 'anthro') return { name: 'datasets_anthro' };
  if (parts[0] === 'datasets' && parts[1] === 'abilities') return { name: 'datasets_abilities' };
  if (parts[0] === 'admin') return { name: 'admin' };
  return { name: 'login' };
}

export function href(to: Route): string {
  if (to.name === 'login') return '#/login';
  if (to.name === 'projects') return '#/projects';
  if (to.name === 'project') return `#/projects/${to.id}`;
  if (to.name === 'artifacts') return `#/projects/${to.id}/artifacts`;
  if (to.name === 'evaluation') return `#/evaluations/${to.id}`;
  if (to.name === 'project_scenarios') return `#/projects/${to.id}/scenarios`;
  if (to.name === 'rulepacks') return '#/rulepacks';
  if (to.name === 'datasets_anthro') return '#/datasets/anthro';
  if (to.name === 'datasets_abilities') return '#/datasets/abilities';
  if (to.name === 'admin') return '#/admin';
  return '#/login';
}
