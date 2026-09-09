import { useState } from 'react';
import type { StyleProfile } from '@shared/types';

interface Props {
  profile: StyleProfile | null;
  onSeed: () => Promise<void>;
  onReflect: () => Promise<void>;
}

export function ProfileView({ profile, onSeed, onReflect }: Props) {
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    try { await fn(); } finally { setBusy(false); }
  }

  if (!profile) {
    return (
      <div className="profile-empty">
        <p>No style profile exists yet. Seed one from your existing posts:</p>
        <button onClick={() => run(onSeed)} disabled={busy}>
          {busy ? 'Seeding...' : 'Seed profile'}
        </button>
      </div>
    );
  }

  return (
    <div className="profile">
      <div className="profile-actions">
        <button onClick={() => run(onReflect)} disabled={busy}>
          {busy ? 'Reflecting...' : 'Run reflection'}
        </button>
        <button onClick={() => run(onSeed)} disabled={busy}>
          Re-seed from scratch
        </button>
      </div>

      <Section title="Tone" items={profile.tone} />

      <div className="section">
        <h3>Sentence length</h3>
        <p>
          <strong>~{profile.sentenceLength.averageWords} words avg.</strong>{' '}
          {profile.sentenceLength.habit}
        </p>
      </div>

      <Section title="Structural habits" items={profile.structuralHabits} />
      <Section title="Signature phrases" items={profile.signaturePhrases} />
      <Section title="Things I never do" items={profile.thingsINeverDo} />
      <Section title="Topics I care about" items={profile.topicsICareAbout} />

      <div className="section">
        <h3>Platform quirks</h3>
        <dl>
          {Object.entries(profile.platformQuirks).map(([k, v]) => (
            <div key={k} className="kv">
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="section">
      <h3>{title}</h3>
      <ul>
        {items.map((i) => <li key={i}>{i}</li>)}
      </ul>
    </div>
  );
}
