import type { MidiItem } from "../types/midi";

interface Props {
  item: MidiItem;
}

/**
 * Wraps the html-midi-player web component.
 *
 * Two deliberate choices for local/offline use:
 *  1. `sound-font` attribute is omitted → html-midi-player falls back to
 *     mm.Player (Tone.js oscillators) and makes no external network requests.
 *  2. The `file_url` from the API may contain the Docker-internal hostname
 *     (e.g. http://backend:8000/…) which the browser cannot resolve.  We strip
 *     the origin so the request goes to the same host the page was loaded from,
 *     passing through Vite's /api proxy to the real backend.
 */
function toProxiedUrl(rawUrl: string): string {
  try {
    const u = new URL(rawUrl);
    // Keep only pathname + search + hash — resolved relative to the page origin
    return u.pathname + u.search + u.hash;
  } catch {
    return rawUrl; // already a relative path — leave it alone
  }
}

export default function MidiPlayer({ item }: Props) {
  return (
    <div className="player-section">
      <div className="player-label">🎹 Player</div>
      {item.file_missing ? (
        <p style={{ color: "var(--red)", fontSize: 13 }}>
          File not found on disk.
        </p>
      ) : (
        <midi-player
          src={toProxiedUrl(item.file_url)}
          style={{ width: "100%" }}
        />
      )}
    </div>
  );
}
