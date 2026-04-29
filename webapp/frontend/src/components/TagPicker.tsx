import { useState, useRef } from "react";

interface Props {
  tags: string[];
  onChange: (tags: string[]) => void;
}

export default function TagPicker({ tags, onChange }: Props) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addTag = () => {
    const name = input.trim().toLowerCase();
    if (name && !tags.includes(name)) {
      onChange([...tags, name]);
    }
    setInput("");
    inputRef.current?.focus();
  };

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag();
    }
    if (e.key === "Backspace" && input === "" && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  };

  return (
    <div className="tag-input-wrap">
      <div className="tag-chips">
        {tags.map((tag) => (
          <span key={tag} className="tag-chip">
            {tag}
            <span className="remove" onClick={() => removeTag(tag)}>✕</span>
          </span>
        ))}
      </div>
      <div className="tag-input-row">
        <input
          ref={inputRef}
          type="text"
          value={input}
          placeholder="Add tag (Enter or comma)…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn btn-ghost btn-sm" onClick={addTag} type="button">
          + Add
        </button>
      </div>
    </div>
  );
}
