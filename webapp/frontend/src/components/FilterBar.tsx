import { useState, useCallback, useRef } from "react";
import type { MidiFilters } from "../types/midi";
import { triggerScan, revalidateMidis } from "../api/midis";

interface Props {
  filters: MidiFilters;
  onFiltersChange: (f: Partial<MidiFilters>) => void;
  resultCount: number;
}

export default function FilterBar({ filters, onFiltersChange, resultCount }: Props) {
  const [scanning, setScanning] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onFiltersChange({ search: value || undefined, page: 1 });
      }, 300);
    },
    [onFiltersChange]
  );

  const handleMinRating = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = parseInt(e.target.value);
    onFiltersChange({ min_rating: val > 0 ? val : undefined, page: 1 });
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await triggerScan();
      await revalidateMidis();
      alert(`Scan complete — ${result.total_items} total items in database.`);
    } catch {
      alert("Scan failed. Check the backend logs.");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="topbar">
      <input
        type="text"
        placeholder="Search melodies…"
        defaultValue={filters.search || ""}
        onChange={handleSearch}
      />

      <select
        value={filters.min_rating ?? 0}
        onChange={handleMinRating}
        title="Minimum rating"
      >
        <option value={0}>All ratings</option>
        {[5, 6, 7, 8, 9, 10].map((r) => (
          <option key={r} value={r}>
            ⭐ {r}+
          </option>
        ))}
      </select>

      <span style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>
        {resultCount} items
      </span>

      <button
        className="btn btn-ghost btn-sm"
        onClick={handleScan}
        disabled={scanning}
        title="Re-scan MIDI directories"
      >
        {scanning ? "⏳" : "🔄"} Scan
      </button>
    </div>
  );
}
