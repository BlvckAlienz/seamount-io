import React, { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { jwtDecode } from 'jwt-decode';

const AuthDebugPage: React.FC = () => {
  const [session, setSession] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [token, setToken] = useState<string | null>(null);
  const [decodedToken, setDecodedToken] = useState<any>(null);

  useEffect(() => {
    const getSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setSession(session);
      setUser(session?.user ?? null);
      setToken(session?.access_token ?? null);
      
      if (session?.access_token) {
        try {
          setDecodedToken(jwtDecode(session.access_token));
        } catch (e) {
          console.error('Error decoding token:', e);
        }
      }
    };

    getSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setToken(session?.access_token ?? null);
        
        if (session?.access_token) {
          try {
            setDecodedToken(jwtDecode(session.access_token));
          } catch (e) {
            console.error('Error decoding token:', e);
          }
        }
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Auth Debug Page</h1>
      
      <h2>Environment Variables</h2>
      <p><strong>VITE_SUPABASE_URL:</strong> {import.meta.env.VITE_SUPABASE_URL}</p>
      <p><strong>VITE_SUPABASE_ANON_KEY:</strong> {import.meta.env.VITE_SUPABASE_ANON_KEY?.substring(0, 20)}...</p>
      
      <h2>Current Auth State</h2>
      <p><strong>Session:</strong> {session ? 'Present' : 'None'}</p>
      <p><strong>User:</strong> {user ? 'Present' : 'None'}</p>
      
      <h2>JWT Token</h2>
      <p><strong>Token:</strong> {token ? token.substring(0, 50) + '...' : 'No token'}</p>
      
      {decodedToken && (
        <>
          <h3>Decoded Token</h3>
          <pre>{JSON.stringify(decodedToken, null, 2)}</pre>
          <p><strong>Issuer (iss):</strong> {decodedToken.iss}</p>
          <p><strong>Audience (aud):</strong> {decodedToken.aud}</p>
          <p><strong>Expiration:</strong> {new Date(decodedToken.exp * 1000).toISOString()}</p>
        </>
      )}
    </div>
  );
};

export default AuthDebugPage;