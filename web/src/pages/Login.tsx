import React, { useState } from 'react';
import Layout from '../components/Layout';
import { api } from '../lib/api';
import { setToken } from '../lib/auth';
import { href } from '../router';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const token = await api.login(email.trim(), password);
      setToken(token);
      window.location.hash = href({ name: 'projects' });
    } catch (err: any) {
      setError(err.message || 'Login failed');
    }
  };
  return (
    <Layout>
      <h1>Login</h1>
      <div className="space" />
      <form onSubmit={onSubmit} aria-label="Login form">
        <label htmlFor="email">Email</label>
        <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label htmlFor="password">Password</label>
        <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <div className="space" />
        <button type="submit">Login</button>
        {error && <div role="alert" className="muted">{error}</div>}
      </form>
    </Layout>
  );
}
