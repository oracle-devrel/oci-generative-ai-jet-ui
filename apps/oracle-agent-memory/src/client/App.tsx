import { useEffect, useState } from 'react';
import { PostComposer } from './components/PostComposer';
import { ProfileView } from './components/ProfileView';
import { api } from './api';
import type { StyleProfile } from '@shared/types';

export function App() {
  const [userId, setUserId] = useState<string | null>(null);
  const [profile, setProfile] = useState<StyleProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'compose' | 'profile'>('compose');

  useEffect(() => {
    (async () => {
      try {
        const me = await api.me();
        setUserId(me.userId);
        const { profile } = await api.loadProfile(me.userId);
        setProfile(profile);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function handleSeed() {
    if (!userId) return;
    const { profile } = await api.seedProfile(userId);
    setProfile(profile);
  }

  async function handleReflect() {
    if (!userId) return;
    const { profile } = await api.reflect(userId);
    setProfile(profile);
  }

  if (loading || !userId) return <div className="loading">Loading...</div>;

  return (
    <div className="app">
      <header>
        <h1>Agent Memory</h1>
        <nav>
          <button
            className={tab === 'compose' ? 'active' : ''}
            onClick={() => setTab('compose')}
          >
            Compose
          </button>
          <button
            className={tab === 'profile' ? 'active' : ''}
            onClick={() => setTab('profile')}
          >
            Style Profile
          </button>
        </nav>
      </header>

      <main>
        {!profile && (
          <div className="banner">
            No style profile yet.{' '}
            <button onClick={handleSeed}>Seed from existing posts</button>
          </div>
        )}

        {tab === 'compose' ? (
          <PostComposer userId={userId} hasProfile={!!profile} />
        ) : (
          <ProfileView
            profile={profile}
            onReflect={handleReflect}
            onSeed={handleSeed}
          />
        )}
      </main>
    </div>
  );
}
