import type { MidiItem } from "../types/midi";

interface Props {
  items: MidiItem[];
  selectedId: number | null;
  onSelect: (item: MidiItem) => void;
  onFavoriteToggle: (item: MidiItem) => void;
}

function ApprovalIcon({ approved }: { approved: boolean | null }) {
  if (approved === true)  return <span className="approved" title="Approved">✅</span>;
  if (approved === false) return <span className="rejected" title="Rejected">❌</span>;
  return <span style={{ color: "var(--muted)" }} title="Not reviewed">○</span>;
}

export default function MidiTable({ items, selectedId, onSelect, onFavoriteToggle }: Props) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        No melodies found.<br />
        <small>Drop .mid files into <code>webapp/media/midis/dataset/</code> or <code>generated/</code> and click "🔄 Scan".</small>
      </div>
    );
  }

  return (
    <div className="midi-list">
      <div className="list-header">
        <span>Name</span>
        <span>Tags</span>
        <span>Rating</span>
        <span>Status</span>
      </div>
      {items.map((item) => (
        <div
          key={item.id}
          className={[
            "midi-row",
            selectedId === item.id ? "selected" : "",
            item.file_missing ? "missing" : "",
          ]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onSelect(item)}
        >
          {/* Name + source badge */}
          <div>
            <div className="midi-row-name">{item.name}</div>
            <div className="midi-row-source">
              <span className={`badge badge-${item.source_type}`}>
                {item.source_type}
              </span>
              {item.duration_seconds != null && (
                <span style={{ marginLeft: 6, color: "var(--muted)", fontSize: 11 }}>
                  {item.duration_seconds.toFixed(1)}s
                </span>
              )}
            </div>
          </div>

          {/* Tags */}
          <div className="tag-chips">
            {item.tags.slice(0, 3).map((t) => (
              <span key={t} className="tag-chip">{t}</span>
            ))}
            {item.tags.length > 3 && (
              <span className="tag-chip">+{item.tags.length - 3}</span>
            )}
          </div>

          {/* Rating */}
          <div>
            {item.rating != null ? (
              <span style={{ color: "var(--yellow)", fontWeight: 600 }}>
                ⭐ {item.rating}
              </span>
            ) : (
              <span style={{ color: "var(--muted)" }}>—</span>
            )}
          </div>

          {/* Status icons */}
          <div className="status-icons">
            <ApprovalIcon approved={item.approved} />
            <span
              className={item.favorite ? "fav-on" : "fav-off"}
              title={item.favorite ? "Remove from favorites" : "Add to favorites"}
              onClick={(e) => {
                e.stopPropagation();
                onFavoriteToggle(item);
              }}
            >
              {item.favorite ? "⭐" : "☆"}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
