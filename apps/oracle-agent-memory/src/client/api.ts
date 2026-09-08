import type {
  DraftRequest,
  DraftResponse,
  SavePostRequest,
  StyleProfile,
} from '@shared/types';

async function jsonFetch<T>(url: string, opts: RequestInit = {}): Promise<T> {
  const r = await fetch(url, {
    headers: { 'content-type': 'application/json' },
    ...opts,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

export const api = {
  me: () => jsonFetch<{ userId: string }>('/api/me'),

  draft: (body: DraftRequest) =>
    jsonFetch<DraftResponse>('/api/draft', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  savePost: (body: SavePostRequest) =>
    jsonFetch<{ id: string }>('/api/posts', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  forgetPost: (id: string, userId: string) =>
    jsonFetch<{ ok: true }>(`/api/posts/${id}`, {
      method: 'DELETE',
      body: JSON.stringify({ userId }),
    }),

  loadProfile: (userId: string) =>
    jsonFetch<{ profile: StyleProfile | null }>(`/api/profile/${userId}`),

  seedProfile: (userId: string) =>
    jsonFetch<{ profile: StyleProfile }>(`/api/profile/${userId}/seed`, {
      method: 'POST',
    }),

  reflect: (userId: string) =>
    jsonFetch<{ profile: StyleProfile }>(`/api/profile/${userId}/reflect`, {
      method: 'POST',
    }),
};
