import { useRef, useState } from "react";
import { enrichBook, type BookEnrichment, type WishlistBook } from "../api";

type InputMode = "title" | "link" | "photo";

const EDITION_LANGUAGES = [
  { value: "", label: "Auto (from cover / title)" },
  { value: "pl", label: "Polish" },
  { value: "en", label: "English" },
  { value: "de", label: "German" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
  { value: "cs", label: "Czech" },
  { value: "uk", label: "Ukrainian" },
] as const;

function languageLabel(code: string | null | undefined): string {
  if (!code) return "";
  return EDITION_LANGUAGES.find((l) => l.value === code)?.label ?? code.toUpperCase();
}

interface AddWishlistFormProps {
  onSubmit: (data: {
    title: string;
    author?: string | null;
    note?: string | null;
    cover_url?: string | null;
    source_url?: string | null;
    total_pages?: number | null;
  }) => Promise<void>;
}

export function AddWishlistForm({ onSubmit }: AddWishlistFormProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<InputMode>("title");
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [enriched, setEnriched] = useState<BookEnrichment | null>(null);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [note, setNote] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [totalPages, setTotalPages] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [editionLanguage, setEditionLanguage] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setQuery("");
    setUrl("");
    setImage(null);
    setImagePreview(null);
    setEnriched(null);
    setTitle("");
    setAuthor("");
    setNote("");
    setSourceUrl("");
    setTotalPages("");
    setCoverUrl("");
    setEditionLanguage("");
    setError(null);
  };

  const close = () => {
    reset();
    setOpen(false);
  };

  const handleImageChange = (file: File | null) => {
    setImage(file);
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(file ? URL.createObjectURL(file) : null);
    setEnriched(null);
  };

  const handleLookup = async () => {
    setError(null);
    setLookupLoading(true);
    try {
      const result = await enrichBook({
        title: mode === "title" ? query : undefined,
        url: mode === "link" ? url : undefined,
        image: mode === "photo" ? image ?? undefined : undefined,
        language: editionLanguage || undefined,
      });
      setEnriched(result);
      setTitle(result.title);
      setAuthor(result.author ?? "");
      setTotalPages(result.total_pages ? String(result.total_pages) : "");
      setCoverUrl(result.cover_url ?? "");
      if (mode === "link" && url.trim()) setSourceUrl(url.trim());
      if (result.language) setEditionLanguage(result.language);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setLookupLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    const pages = totalPages ? parseInt(totalPages, 10) : null;
    setSaveLoading(true);
    try {
      await onSubmit({
        title: title.trim(),
        author: author.trim() || null,
        note: note.trim() || null,
        cover_url: coverUrl.trim() || null,
        source_url: sourceUrl.trim() || null,
        total_pages: pages && pages > 0 ? pages : null,
      });
      close();
    } finally {
      setSaveLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full rounded-xl border border-dashed border-slate-700 py-3 text-sm text-slate-400 hover:border-amber-500 hover:text-amber-300"
      >
        + Add to buy list
      </button>
    );
  }

  const canLookup =
    (mode === "title" && query.trim()) ||
    (mode === "link" && url.trim()) ||
    (mode === "photo" && image);

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <p className="text-xs text-slate-500">
        Save interesting titles from screenshots, links or quick notes — buy later.
      </p>

      <div className="flex gap-2">
        {(["title", "link", "photo"] as InputMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => {
              setMode(m);
              setEnriched(null);
              setError(null);
            }}
            className={`rounded-lg px-3 py-1.5 text-xs capitalize ${
              mode === m
                ? "bg-amber-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {m === "title" ? "Title" : m === "link" ? "Link" : "Photo"}
          </button>
        ))}
      </div>

      <label className="block text-xs text-slate-500">
        Edition language
        <select
          value={editionLanguage}
          onChange={(e) => {
            setEditionLanguage(e.target.value);
            setEnriched(null);
          }}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        >
          {EDITION_LANGUAGES.map((lang) => (
            <option key={lang.value || "auto"} value={lang.value}>
              {lang.label}
            </option>
          ))}
        </select>
      </label>

      {mode === "title" && (
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setEnriched(null);
          }}
          placeholder="e.g. Atomic Habits"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
      )}

      {mode === "link" && (
        <input
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setEnriched(null);
          }}
          placeholder="Lubimyczytac, Amazon, Goodreads…"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
      )}

      {mode === "photo" && (
        <div className="space-y-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => handleImageChange(e.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="w-full rounded-lg border border-dashed border-slate-600 py-6 text-sm text-slate-400 hover:border-amber-500"
          >
            {image ? image.name : "Upload screenshot of cover / recommendation"}
          </button>
          {imagePreview && (
            <img
              src={imagePreview}
              alt="Screenshot preview"
              className="mx-auto max-h-48 rounded-lg object-contain"
            />
          )}
        </div>
      )}

      <button
        type="button"
        disabled={!canLookup || lookupLoading}
        onClick={handleLookup}
        className="w-full rounded-lg bg-slate-800 py-2 text-sm text-amber-300 hover:bg-slate-700 disabled:opacity-50"
      >
        {lookupLoading ? "Looking up with AI…" : "✨ Recognize book"}
      </button>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {enriched && (
        <div className="rounded-lg border border-amber-800/40 bg-amber-950/20 p-3 text-xs text-slate-400">
          <p>
            Found via {enriched.source} · confidence: {enriched.confidence}
            {enriched.language ? (
              <> · <span className="text-slate-200">{languageLabel(enriched.language)} edition</span></>
            ) : null}
          </p>
          {enriched.cover_url && (
            <img src={enriched.cover_url} alt="" className="mt-2 h-24 rounded object-contain" />
          )}
        </div>
      )}

      <div className="space-y-3 border-t border-slate-800 pt-4">
        <p className="text-xs text-slate-500">Details (edit freely)</p>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title *"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
          required
        />
        <input
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Author"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Your note — why you want it, where you saw it…"
          rows={3}
          className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
        <input
          value={sourceUrl}
          onChange={(e) => setSourceUrl(e.target.value)}
          placeholder="Source link (optional)"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
        <input
          value={coverUrl}
          onChange={(e) => setCoverUrl(e.target.value)}
          placeholder="Cover URL (optional)"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
        {coverUrl && (
          <img src={coverUrl} alt="Cover preview" className="mx-auto h-32 rounded-lg object-contain" />
        )}
        <input
          type="number"
          min={1}
          value={totalPages}
          onChange={(e) => setTotalPages(e.target.value)}
          placeholder="Pages (optional — needed when moving to shelf)"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-amber-500"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saveLoading || !title.trim()}
          className="rounded-lg bg-amber-600 px-4 py-2 text-sm hover:bg-amber-500 disabled:opacity-50"
        >
          {saveLoading ? "Saving…" : "Save to list"}
        </button>
        <button
          type="button"
          onClick={close}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

interface WishlistCardProps {
  item: WishlistBook;
  onDelete: (id: number) => void;
  onMoveToShelf: (id: number, totalPages?: number) => Promise<void>;
  onUpdateNote: (id: number, note: string | null) => Promise<void>;
}

export function WishlistCard({ item, onDelete, onMoveToShelf, onUpdateNote }: WishlistCardProps) {
  const [moving, setMoving] = useState(false);
  const [pagesInput, setPagesInput] = useState(item.total_pages ? String(item.total_pages) : "");
  const [showMove, setShowMove] = useState(false);
  const [editingNote, setEditingNote] = useState(false);
  const [noteValue, setNoteValue] = useState(item.note ?? "");
  const [error, setError] = useState<string | null>(null);

  const handleMove = async () => {
    setError(null);
    const pages = pagesInput ? parseInt(pagesInput, 10) : item.total_pages;
    if (!pages || pages < 1) {
      setError("Enter page count before adding to shelf");
      return;
    }
    setMoving(true);
    try {
      await onMoveToShelf(item.id, pages);
      setShowMove(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to move");
    } finally {
      setMoving(false);
    }
  };

  const saveNote = async () => {
    await onUpdateNote(item.id, noteValue.trim() || null);
    setEditingNote(false);
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <div className="mb-2 flex gap-3">
        {item.cover_url ? (
          <img
            src={item.cover_url}
            alt=""
            className="h-24 w-16 shrink-0 rounded-md object-cover shadow-sm"
          />
        ) : (
          <div className="flex h-24 w-16 shrink-0 items-center justify-center rounded-md bg-slate-800 text-lg text-slate-600">
            🛒
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold leading-snug">{item.title}</h3>
          {item.author && <p className="text-sm text-slate-400">{item.author}</p>}
          {item.total_pages && (
            <p className="mt-1 text-xs text-slate-500">{item.total_pages} pages</p>
          )}
          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-xs text-amber-400/90 hover:text-amber-300"
            >
              Source link ↗
            </a>
          )}
        </div>
      </div>

      {item.note && !editingNote && (
        <p className="mb-3 whitespace-pre-wrap text-sm text-slate-400">{item.note}</p>
      )}

      {editingNote ? (
        <div className="mb-3 space-y-2">
          <textarea
            value={noteValue}
            onChange={(e) => setNoteValue(e.target.value)}
            rows={3}
            className="w-full resize-y rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-amber-500"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={saveNote}
              className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs hover:bg-amber-500"
            >
              Save note
            </button>
            <button
              type="button"
              onClick={() => {
                setNoteValue(item.note ?? "");
                setEditingNote(false);
              }}
              className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setEditingNote(true)}
          className="mb-3 text-xs text-slate-500 hover:text-amber-300"
        >
          {item.note ? "Edit note" : "+ Add note"}
        </button>
      )}

      {showMove ? (
        <div className="mb-2 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="number"
              min={1}
              value={pagesInput}
              onChange={(e) => setPagesInput(e.target.value)}
              placeholder="Total pages"
              className="w-28 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs outline-none focus:border-amber-500"
            />
            <button
              type="button"
              disabled={moving}
              onClick={handleMove}
              className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs hover:bg-violet-500 disabled:opacity-50"
            >
              {moving ? "…" : "Confirm → shelf"}
            </button>
            <button
              type="button"
              onClick={() => setShowMove(false)}
              className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
            >
              Cancel
            </button>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setShowMove(true)}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs hover:bg-violet-500"
          >
            Bought — add to shelf
          </button>
          <button
            type="button"
            onClick={() => onDelete(item.id)}
            className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-700 hover:text-red-300"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}
