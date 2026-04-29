import type { MidiFilters } from "../types/midi";

interface Props {
  activeFilter: MidiFilters["source_type"];
  onChange: (f: MidiFilters["source_type"]) => void;
}

const ITEMS = [
  { key: "all",        icon: "🎵", label: "All Melodies" },
  { key: "dataset",    icon: "📂", label: "Dataset" },
  { key: "generated",  icon: "⚡", label: "Generated" },
  { key: "favorites",  icon: "⭐", label: "Favorites" },
  { key: "approved",   icon: "✅", label: "Approved" },
  { key: "rejected",   icon: "❌", label: "Rejected" },
  { key: "unreviewed", icon: "🔍", label: "Unreviewed" },
] as const;

export default function Sidebar({ activeFilter, onChange }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-title">Curator</div>
      {ITEMS.map((item) => (
        <button
          key={item.key}
          className={`sidebar-item ${activeFilter === item.key ? "active" : ""}`}
          onClick={() => onChange(item.key)}
        >
          <span className="icon">{item.icon}</span>
          {item.label}
        </button>
      ))}
    </aside>
  );
}
