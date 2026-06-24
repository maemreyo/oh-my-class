/**
 * In-memory TTL store for rendered artifacts awaiting preview.
 * No database — artifacts are transient, expire after TTL.
 */

interface StoredArtifact {
  html: string;
  type: string;
  createdAt: number;
  ttlMs: number;
}

export class PreviewStore {
  private _store = new Map<string, StoredArtifact>();
  private _ttlMs: number;

  constructor(ttlMs = 60 * 60 * 1000) {
    this._ttlMs = ttlMs;
  }

  set(runId: string, html: string, type: string): void {
    this._store.set(runId, {
      html,
      type,
      createdAt: Date.now(),
      ttlMs: this._ttlMs,
    });
  }

  get(runId: string): StoredArtifact | null {
    const entry = this._store.get(runId);
    if (!entry) return null;
    if (Date.now() - entry.createdAt > entry.ttlMs) {
      this._store.delete(runId);
      return null;
    }
    return entry;
  }

  delete(runId: string): void {
    this._store.delete(runId);
  }

  purgeExpired(): number {
    let count = 0;
    const now = Date.now();
    for (const [id, entry] of this._store) {
      if (now - entry.createdAt > entry.ttlMs) {
        this._store.delete(id);
        count++;
      }
    }
    return count;
  }
}

export const previewStore = new PreviewStore();
