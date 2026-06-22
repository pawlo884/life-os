import { useRef, useState } from "react";
import { enrichBook, type Book, type BookEnrichment, type ReadingLog } from "../api";

type InputMode = "title" | "link" | "photo";

interface AddBookFormProps {
  onSubmit: (data: { title: string; author: string; total_pages: number }) => Promise<void>;
}

export function AddBookForm({ onSubmit }: AddBookFormProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<InputMode>("title");
  const [query, setQuery] = useState("");
  const [url, setUrl] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [enriched, setEnriched] = useState<BookEnrichment | null>(null);
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [totalPages, setTotalPages] = useState("");
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
    setTotalPages("");
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
      });
      setEnriched(result);
      setTitle(result.title);
      setAuthor(result.author ?? "");
      setTotalPages(result.total_pages ? String(result.total_pages) : "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed");
    } finally {
      setLookupLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const pages = parseInt(totalPages, 10);
    if (!title || !pages) return;
    setSaveLoading(true);
    try {
      await onSubmit({ title, author, total_pages: pages });
      close();
    } finally {
      setSaveLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full rounded-xl border border-dashed border-slate-700 py-3 text-sm text-slate-400 hover:border-violet-500 hover:text-violet-300"
      >
        + Add a book
      </button>
    );
  }

  const canLookup =
    (mode === "title" && query.trim()) ||
    (mode === "link" && url.trim()) ||
    (mode === "photo" && image);

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
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
                ? "bg-violet-600 text-white"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700"
            }`}
          >
            {m === "title" ? "Title" : m === "link" ? "Link" : "Photo"}
          </button>
        ))}
      </div>

      {mode === "title" && (
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setEnriched(null);
          }}
          placeholder="e.g. Fluent Python"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
        />
      )}

      {mode === "link" && (
        <input
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            setEnriched(null);
          }}
          placeholder="Goodreads, Amazon, publisher page…"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
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
            className="w-full rounded-lg border border-dashed border-slate-600 py-6 text-sm text-slate-400 hover:border-violet-500"
          >
            {image ? image.name : "Upload cover photo"}
          </button>
          {imagePreview && (
            <img
              src={imagePreview}
              alt="Cover preview"
              className="mx-auto h-40 rounded-lg object-contain"
            />
          )}
        </div>
      )}

      <button
        type="button"
        disabled={!canLookup || lookupLoading}
        onClick={handleLookup}
        className="w-full rounded-lg bg-slate-800 py-2 text-sm text-violet-300 hover:bg-slate-700 disabled:opacity-50"
      >
        {lookupLoading ? "Looking up with AI…" : "✨ Find book details"}
      </button>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {enriched && (
        <div className="rounded-lg border border-violet-800/40 bg-violet-950/20 p-3 text-xs text-slate-400">
          Found via {enriched.source} · confidence: {enriched.confidence}
          {enriched.cover_url && (
            <img
              src={enriched.cover_url}
              alt=""
              className="mt-2 h-24 rounded object-contain"
            />
          )}
        </div>
      )}

      <div className="space-y-3 border-t border-slate-800 pt-4">
        <p className="text-xs text-slate-500">Review and edit before saving</p>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
          required
        />
        <input
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="Author"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
        />
        <input
          type="number"
          min={1}
          value={totalPages}
          onChange={(e) => setTotalPages(e.target.value)}
          placeholder="Total pages"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
          required
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saveLoading || !title || !totalPages}
          className="rounded-lg bg-violet-600 px-4 py-2 text-sm hover:bg-violet-500 disabled:opacity-50"
        >
          {saveLoading ? "Saving…" : "Add to shelf"}
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

interface BookCardProps {
  book: Book;
  onActivate: (id: number) => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  selected: boolean;
}

export function BookCard({ book, onActivate, onSelect, onDelete, selected }: BookCardProps) {
  const [confirming, setConfirming] = useState(false);

  const handleDelete = () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    onDelete(book.id);
    setConfirming(false);
  };

  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        selected
          ? "border-violet-500 bg-violet-950/30"
          : "border-slate-800 bg-slate-900/50 hover:border-slate-700"
      }`}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold">{book.title}</h3>
          {book.author && <p className="text-sm text-slate-400">{book.author}</p>}
        </div>
        <div className="flex gap-1">
          {book.is_active && (
            <span className="rounded-full bg-violet-600/30 px-2 py-0.5 text-xs text-violet-300">
              Active
            </span>
          )}
          <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
            {book.status}
          </span>
        </div>
      </div>

      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-400">
          {book.current_page} / {book.total_pages} pages
        </span>
        <span className="text-violet-400">{book.completion_percent}%</span>
      </div>
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-violet-500 transition-all"
          style={{ width: `${book.completion_percent}%` }}
        />
      </div>

      {book.estimated_completion_date && book.status === "READING" && (
        <p className="mb-3 text-xs text-slate-500">
          Est. finish: {book.estimated_completion_date}
          {book.avg_pages_per_day ? ` · ${book.avg_pages_per_day} ppd` : ""}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onSelect(book.id)}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
        >
          History
        </button>
        {!book.is_active && book.status !== "COMPLETED" && (
          <button
            onClick={() => onActivate(book.id)}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs hover:bg-violet-500"
          >
            Set active
          </button>
        )}
        <button
          onClick={handleDelete}
          onBlur={() => setConfirming(false)}
          className={`rounded-lg px-3 py-1.5 text-xs ${
            confirming
              ? "bg-red-600 text-white hover:bg-red-500"
              : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-red-300"
          }`}
        >
          {confirming ? "Confirm delete" : "Delete"}
        </button>
      </div>
    </div>
  );
}

interface ReadingHistoryProps {
  logs: ReadingLog[];
  bookTitle: string;
}

export function ReadingHistory({ logs, bookTitle }: ReadingHistoryProps) {
  if (logs.length === 0) {
    return <p className="text-sm text-slate-500">No reading sessions yet for {bookTitle}.</p>;
  }

  return (
    <div className="space-y-2">
      {logs.map((log) => (
        <div
          key={log.id}
          className="flex items-center justify-between rounded-lg bg-slate-800/60 px-4 py-2 text-sm"
        >
          <span className="text-slate-300">{log.log_date}</span>
          <span className="font-medium text-violet-300">+{log.pages_read} pages</span>
        </div>
      ))}
    </div>
  );
}

interface LogPagesFormProps {
  onSubmit: (pages: number) => Promise<void>;
  activeBookTitle: string | null;
}

export function LogPagesForm({ onSubmit, activeBookTitle }: LogPagesFormProps) {
  const [pages, setPages] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = parseInt(pages, 10);
    if (!value || value <= 0) return;
    setLoading(true);
    try {
      await onSubmit(value);
      setPages("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="number"
        min={1}
        value={pages}
        onChange={(e) => setPages(e.target.value)}
        placeholder="Pages read"
        className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-medium hover:bg-violet-500 disabled:opacity-50"
      >
        {loading ? "..." : "Log"}
      </button>
      {activeBookTitle && <p className="sr-only">Logging to {activeBookTitle}</p>}
    </form>
  );
}
