'use client';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { supabase } from '../lib/supabaseClient';
import { useRouter } from 'next/navigation';

const COUNTRIES = ['CMR', 'GAB', 'COG', 'TCD', 'CAF', 'GNQ'];
const COUNTRY_NAMES: Record<string, string> = { CMR: '🇨🇲 Cameroun', GAB: '🇬🇦 Gabon', COG: '🇨🇬 Congo', TCD: '🇹🇩 Tchad', CAF: '🇨🇫 RCA', GNQ: '🇬🇶 Guinée Eq.' };

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [country, setCountry] = useState('CMR');
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        setUser(data.session.user);
      } else {
        router.push('/login');
      }
    });
  }, [router]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const token = (await supabase.auth.getSession()).data.session?.access_token;
      const res = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/dashboard/${country}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setData(res.data);
      setHistory(res.data.history || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (user) fetchData(); }, [country, user]);

  const handleLogout = async () => { await supabase.auth.signOut(); router.push('/login'); };

  if (!user) return <div style={{ textAlign: 'center', marginTop: 100 }}>Chargement...</div>;

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: 20, fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #1e293b', paddingBottom: 10 }}>
        <h1>📊 CEIP · Economic Intelligence</h1>
        <div>
          <span style={{ background: '#10b981', padding: '4px 12px', borderRadius: 20, fontSize: 12, color: 'white', marginRight: 10 }}>LIVE</span>
          <span style={{ marginRight: 10 }}>{user.email}</span>
          <button onClick={handleLogout} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '6px 12px', borderRadius: 4, cursor: 'pointer' }}>Déconnexion</button>
        </div>
      </div>

      {/* Sélecteur Pays */}
      <div style={{ margin: '20px 0', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {COUNTRIES.map(c => (
          <button key={c} onClick={() => setCountry(c)} 
                  style={{ padding: '8px 16px', borderRadius: 6, border: country === c ? '2px solid #2563eb' : '1px solid #ccc', 
                           background: country === c ? '#2563eb' : 'white', color: country === c ? 'white' : '#333', fontWeight: 600 }}>
            {COUNTRY_NAMES[c]}
          </button>
        ))}
      </div>

      {loading ? <p>Chargement des indicateurs...</p> : (
        <>
          {/* KPI */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 30 }}>
            <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, borderLeft: '4px solid #2563eb' }}>
              <p style={{ color: '#64748b', margin: 0 }}>PIB Croissance</p>
              <h2 style={{ margin: 0, fontSize: 28 }}>{data?.latest_gdp ?? 'N/A'}%</h2>
            </div>
            <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, borderLeft: '4px solid #eab308' }}>
              <p style={{ color: '#64748b', margin: 0 }}>Inflation</p>
              <h2 style={{ margin: 0, fontSize: 28 }}>{data?.latest_inflation ?? 'N/A'}%</h2>
            </div>
            <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, borderLeft: '4px solid #ef4444' }}>
              <p style={{ color: '#64748b', margin: 0 }}>Dette / PIB</p>
              <h2 style={{ margin: 0, fontSize: 28 }}>{data?.debt_ratio ?? 'N/A'}%</h2>
            </div>
            <div style={{ background: '#f8fafc', padding: 20, borderRadius: 12, borderLeft: '4px solid #8b5cf6' }}>
              <p style={{ color: '#64748b', margin: 0 }}>Economic Health</p>
              <h2 style={{ margin: 0, fontSize: 28 }}>{data?.health_score ?? 0}/100</h2>
            </div>
          </div>

          {/* Graphique */}
          <div style={{ background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
            <h3>Évolution du PIB</h3>
            <div style={{ height: 350 }}>
              <ResponsiveContainer>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Export PDF */}
          <div style={{ marginTop: 20 }}>
            <button onClick={async () => {
              const token = (await supabase.auth.getSession()).data.session?.access_token;
              window.open(`${process.env.NEXT_PUBLIC_API_URL}/reports/${country}?token=${token}`, '_blank');
            }} style={{ background: '#1e293b', color: 'white', padding: '12px 24px', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
              📄 Télécharger le Rapport CEIP (PDF)
            </button>
          </div>
        </>
      )}
    </div>
  );
}