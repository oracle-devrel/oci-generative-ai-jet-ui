import { useState } from 'react';
import { api } from '../api';
import type { DraftResponse } from '@shared/types';

interface Props {
  userId: string;
  hasProfile: boolean;
}

export function PostComposer({ userId, hasProfile }: Props) {
  const [platform, setPlatform] = useState('linkedin');
  const [topic, setTopic] = useState('');
  const [draft, setDraft] = useState('');
  const [basedOn, setBasedOn] = useState<DraftResponse['basedOn']>([]);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleDraft() {
    if (!topic.trim()) return;
    setBusy(true);
    setSaved(false);
    try {
      const r = await api.draft({ userId, platform, topic });
      setDraft(r.draft);
      setBasedOn(r.basedOn);
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    if (!draft.trim()) return;
    setBusy(true);
    try {
      await api.savePost({ userId, platform, topic, content: draft });
      setSaved(true);
      setDraft('');
      setTopic('');
      setBasedOn([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="composer">
      <div className="row">
        <label>
          Platform
          <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="linkedin">LinkedIn</option>
            <option value="x">X / Twitter</option>
            <option value="bluesky">Bluesky</option>
          </select>
        </label>
        <label className="grow">
          Topic
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="What should this post be about?"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleDraft();
            }}
          />
        </label>
        <button
          className="primary"
          onClick={handleDraft}
          disabled={busy || !topic.trim() || !hasProfile}
        >
          {busy ? 'Drafting...' : 'Draft post'}
        </button>
      </div>

      {!hasProfile && (
        <p className="hint">
          Seed a style profile first (Style Profile tab) before drafting.
        </p>
      )}

      {draft && (
        <>
          <textarea
            className="draft"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={12}
          />
          <div className="actions">
            <button onClick={handleSave} disabled={busy}>
              Save as published
            </button>
            <button onClick={() => setDraft('')} disabled={busy}>
              Discard
            </button>
            {saved && <span className="saved">✓ saved</span>}
          </div>

          {basedOn.length > 0 && (
            <details className="based-on">
              <summary>Based on {basedOn.length} similar posts</summary>
              <ul>
                {basedOn.map((b) => (
                  <li key={b.postId}>
                    <code>{b.distance.toFixed(3)}</code>{' '}
                    {b.topic ?? '(no topic)'}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}
