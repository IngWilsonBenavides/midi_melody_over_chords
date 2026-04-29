import { useState, useEffect } from "react";
import type { MidiItem, FeedbackPayload } from "../types/midi";
import { saveFeedback, revalidateMidis } from "../api/midis";
import TagPicker from "./TagPicker";

interface Props {
  item: MidiItem;
  onUpdated: (updated: MidiItem) => void;
}

export default function FeedbackPanel({ item, onUpdated }: Props) {
  const [rating, setRating]   = useState<number | null>(item.rating);
  const [approved, setApproved] = useState<boolean | null>(item.approved);
  const [favorite, setFavorite] = useState(item.favorite);
  const [tags, setTags]       = useState<string[]>(item.tags);
  const [notes, setNotes]     = useState(item.notes);
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);

  // Sync when item changes (user clicked a different row)
  useEffect(() => {
    setRating(item.rating);
    setApproved(item.approved);
    setFavorite(item.favorite);
    setTags(item.tags);
    setNotes(item.notes);
    setSaved(false);
  }, [item.id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: FeedbackPayload = {
        rating,
        approved,
        favorite,
        tags,
        notes,
      };
      const updated = await saveFeedback(item.id, payload);
      onUpdated(updated);
      await revalidateMidis();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save feedback", err);
      alert("Failed to save. Check the console.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="feedback-section">
      {/* ── Approve / Reject ────────────────────────────────────────────── */}
      <div>
        <div className="feedback-label">Decision</div>
        <div className="approve-btns">
          <button
            className={`approve-btn ${approved === true ? "active-approve" : ""}`}
            onClick={() => setApproved(approved === true ? null : true)}
            type="button"
          >
            ✅ Approve
          </button>
          <button
            className={`approve-btn ${approved === false ? "active-reject" : ""}`}
            onClick={() => setApproved(approved === false ? null : false)}
            type="button"
          >
            ❌ Reject
          </button>
          <button
            className={`fav-btn ${favorite ? "active" : ""}`}
            onClick={() => setFavorite(!favorite)}
            title="Toggle favorite"
            type="button"
          >
            {favorite ? "⭐" : "☆"}
          </button>
        </div>
      </div>

      {/* ── Rating ──────────────────────────────────────────────────────── */}
      <div>
        <div className="feedback-label">Rating</div>
        <div className="rating-row">
          <input
            type="range"
            min={1}
            max={10}
            value={rating ?? 5}
            onChange={(e) => setRating(parseInt(e.target.value))}
            style={{ flex: 1 }}
          />
          <span className="rating-value">{rating ?? "—"}</span>
          {rating != null && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setRating(null)}
              type="button"
              title="Clear rating"
            >
              ✕
            </button>
          )}
        </div>
        {/* Star display */}
        <div className="star-rating" style={{ marginTop: 4 }}>
          {Array.from({ length: 10 }, (_, i) => (
            <span
              key={i + 1}
              className={`star ${rating != null && i + 1 <= rating ? "on" : ""}`}
              onClick={() => setRating(i + 1)}
            >
              ★
            </span>
          ))}
        </div>
      </div>

      {/* ── Tags ────────────────────────────────────────────────────────── */}
      <div>
        <div className="feedback-label">Tags / Genre</div>
        <TagPicker tags={tags} onChange={setTags} />
      </div>

      {/* ── Notes ───────────────────────────────────────────────────────── */}
      <div>
        <div className="feedback-label">Notes</div>
        <textarea
          className="notes-textarea"
          placeholder="Free notes about this melody…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
      </div>

      {/* ── Save ────────────────────────────────────────────────────────── */}
      <div className="save-row">
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saving}
          type="button"
        >
          {saving ? "Saving…" : "💾 Save Feedback"}
        </button>
        {saved && <span className="save-status">✓ Saved!</span>}
      </div>
    </div>
  );
}
