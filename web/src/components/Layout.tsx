import React from 'react';
import { href } from '../router';
import { isAuthed, setToken } from '../lib/auth';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container">
      <nav className="nav" aria-label="Primary">
        <div>
          <a href={href({ name: 'projects' })} aria-label="Projects">IDP</a>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <a href={href({ name: 'rulepacks' })} aria-label="Rulepacks">Rulepacks</a>
          <a href={href({ name: 'datasets_anthro' })} aria-label="Anthropometrics">Anthro</a>
          <a href={href({ name: 'datasets_abilities' })} aria-label="Abilities">Abilities</a>
          <a href={href({ name: 'admin' })} aria-label="Admin">Admin</a>
          {isAuthed() ? (
            <button aria-label="Logout" onClick={() => { setToken(null); window.location.hash = '#/login'; }}>Logout</button>
          ) : null}
        </div>
      </nav>
      <div className="panel" role="main">{children}</div>
    </div>
  );
}
