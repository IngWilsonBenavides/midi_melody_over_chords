import type { MidiItem } from "../types/midi";

interface Props {
  item: MidiItem;
}

/**
 * Wraps the html-midi-player web component.
 * The component loads sounds from the default Magenta soundfont CDN.
 * If the browser has no internet access the piano will not load — a known
 * limitation of this MVP; a self-hosted soundfont can be configured later.
 */
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
          src={item.file_url}
          sound-font="https://storage.googleapis.com/magentadata/soundfonts/sgm_plus"
          style={{ width: "100%" }}
        />
      )}
    </div>
  );
}
