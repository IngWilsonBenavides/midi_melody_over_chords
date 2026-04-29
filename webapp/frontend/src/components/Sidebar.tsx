import type { MidiFilters } from "../types/midi";

interface Props {
  activeFilter: MidiFilters["source_type"];
  onChange: (f: MidiFilters["source_type"]) => void;
  collapsed: boolean;
  onToggle: () => void;
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

export default function Sidebar({ activeFilter, onChange, collapsed, onToggle }: Props) {
  return (
    <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`}>
      <button
        className="sidebar-toggle"
        onClick={onToggle}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? "☰" : "✕"}
      </button>

      {!collapsed && <div className="sidebar-title">Curator</div>}

      {ITEMS.map((item) => (
        <button
          key={item.key}
          className={`sidebar-item ${activeFilter === item.key ? "active" : ""}`}
          onClick={() => { onChange(item.key); }}
          title={collapsed ? item.label : undefined}
          aria-label={item.label}
        >
          <span className="icon">{item.icon}</span>
          {!collapsed && <span className="sidebar-item-label">{item.label}</span>}
        </button>
      ))}
    </aside>
  );
}
