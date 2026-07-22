'use client';
import { supabase } from '../../lib/supabaseClient';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      alert('Erreur: ' + error.message);
    } else {
      router.push('/');
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', padding: 20, border: '1px solid #ddd', borderRadius: 8, textAlign: 'center' }}>
      <h1>CEIP Pro</h1>
      <p>Connectez-vous pour accéder aux données</p>
      <form onSubmit={handleLogin}>
        <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: '100%', padding: 10, marginBottom: 10, border: '1px solid #ccc', borderRadius: 4 }} />
        <input type="password" placeholder="Mot de passe" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: '100%', padding: 10, marginBottom: 10, border: '1px solid #ccc', borderRadius: 4 }} />
        <button type="submit" disabled={loading} style={{ width: '100%', padding: 10, background: '#2563eb', color: 'white', border: 'none', borderRadius: 4 }}>
          {loading ? 'Connexion...' : 'Se connecter'}
        </button>
      </form>
    </div>
  );
}