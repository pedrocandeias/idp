import React, { useEffect, useMemo, useState } from 'react';
import { isAuthed } from './lib/auth';
import { parseRoute } from './router';
import LoginPage from './pages/Login';
import ProjectsPage from './pages/Projects';
import ProjectDetailPage from './pages/ProjectDetail';
import ArtifactsPage from './pages/Artifacts';
import EvaluationDetailPage from './pages/EvaluationDetail';

export default function App() {
  const [hash, setHash] = useState<string>(window.location.hash || '#/login');
  useEffect(() => {
    const onHash = () => setHash(window.location.hash || '#/login');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const route = useMemo(() => parseRoute(hash), [hash]);

  if (!isAuthed() && route.name !== 'login') {
    window.location.hash = '#/login';
    return null;
  }

  switch (route.name) {
    case 'login':
      return <LoginPage />;
    case 'projects':
      return <ProjectsPage />;
    case 'project':
      return <ProjectDetailPage id={route.id} />;
    case 'artifacts':
      return <ArtifactsPage projectId={route.id} />;
    case 'evaluation':
      return <EvaluationDetailPage id={route.id} />;
    default:
      return <LoginPage />;
  }
}
