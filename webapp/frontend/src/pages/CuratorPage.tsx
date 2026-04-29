import { useState, useCallback } from "react";
import type { MidiItem, MidiFilters } from "../types/midi";
import { useMidis, saveFeedback, revalidateMidis } from "../api/midis";
import Sidebar from "../components/Sidebar";
import FilterBar from "../components/FilterBar";
import MidiTable from "../components/MidiTable";
import MidiPlayer from "../components/MidiPlayer";
import FeedbackPanel from "../components/FeedbackPanel";

const DEFAULT_FILTERS: MidiFilters = {
  source_type: "all",
  page: 1,
};

export default function CuratorPage() {
  const [filters, setFilters] = useState<MidiFilters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<MidiItem | null>(null);

  const { data, isLoading, error } = useMidis(filters);

  const items: MidiItem[] = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = data ? Math.ceil(data.count / 50) : 1;

  const updateFilters = useCallback((partial: Partial<MidiFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  }, []);

  const handleSidebarChange = (sourceType: MidiFilters["source_type"]) => {
    setFilters({ source_type: sourceType, page: 1 });
    setSelected(null);
  };

  const handleFavoriteToggle = async (item: MidiItem) => {
    await saveFeedback(item.id, { favorite: !item.favorite });
    await revalidateMidis();
    if (selected?.id === item.id) {
      setSelected((prev) => prev ? { ...prev, favorite: !prev.favorite } : prev);
    }
  };

  const handleUpdated = (updated: MidiItem) => {
    setSelected(updated);
  };

  return (
    <div className="app-layout">
      <Sidebar
        activeFilter={filters.source_type}
        onChange={handleSidebarChange}
      />

      <div className="main-panel">
        <FilterBar
          filters={filters}
          onFiltersChange={updateFilters}
          resultCount={totalCount}
        />

        <div className="split-view">
          {/* ── List column ──────────────────────────────────────────────── */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
            {isLoading && (
              <div className="empty-state">⏳ Loading…</div>
            )}
            {error && (
              <div className="empty-state" style={{ color: "var(--red)" }}>
                ❌ Failed to load. Is the backend running?<br />
                <small>Check http://localhost:8000/api/midis/</small>
              </div>
            )}
            {!isLoading && !error && (
              <MidiTable
                items={items}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
                onFavoriteToggle={handleFavoriteToggle}
              />
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="pagination">
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={(filters.page ?? 1) <= 1}
                  onClick={() => updateFilters({ page: (filters.page ?? 1) - 1 })}
                >
                  ← Prev
                </button>
                <span>
                  Page {filters.page ?? 1} / {totalPages}
                </span>
                <button
                  className="btn btn-ghost btn-sm"
                  disabled={(filters.page ?? 1) >= totalPages}
                  onClick={() => updateFilters({ page: (filters.page ?? 1) + 1 })}
                >
                  Next →
                </button>
              </div>
            )}
          </div>

          {/* ── Detail / feedback column ──────────────────────────────────── */}
          <div className="detail-panel">
            {!selected ? (
              <div className="detail-empty">
                ← Select a melody to play and review it
              </div>
            ) : (
              <>
                <div className="detail-header">
                  <div className="detail-name">{selected.name}</div>
                  <div className="detail-meta">
                    <span className={`badge badge-${selected.source_type}`}>
                      {selected.source_type}
                    </span>
                    {selected.duration_seconds != null && (
                      <span style={{ marginLeft: 8 }}>
                        ⏱ {selected.duration_seconds.toFixed(1)}s
                      </span>
                    )}
                    {selected.file_missing && (
                      <span style={{ marginLeft: 8, color: "var(--red)" }}>⚠ file missing</span>
                    )}
                  </div>
                </div>

                <MidiPlayer item={selected} />

                <FeedbackPanel
                  key={selected.id}
                  item={selected}
                  onUpdated={handleUpdated}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
