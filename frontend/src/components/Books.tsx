import { useRef, useState } from "react";
import { enrichBook, type Book, type BookEnrichment, type ReadingLog } from "../api";

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

interface AddBookFormProps {
  onSubmit: (data: {
    title: string;
    author: string;
    total_pages: number;
    cover_url?: string | null;
  }) => Promise<void>;
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
      if (result.language) setEditionLanguage(result.language);
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
      await onSubmit({
        title,
        author,
        total_pages: pages,
        cover_url: coverUrl.trim() || null,
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

      <label className="block text-xs text-slate-500">
        Edition language
        <select
          value={editionLanguage}
          onChange={(e) => {
            setEditionLanguage(e.target.value);
            setEnriched(null);
          }}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
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
          <p>
            Found via {enriched.source} · confidence: {enriched.confidence}
            {enriched.language ? (
              <> · <span className="text-slate-200">{languageLabel(enriched.language)} edition</span></>
            ) : null}
            {enriched.total_pages ? (
              <> · <span className="text-slate-200">{enriched.total_pages} pages</span></>
            ) : (
              <> · <span className="text-amber-400">page count not found</span></>
            )}
          </p>
          <p className="mt-1 text-amber-300/90">
            Editions and languages vary — verify title and page count before saving.
          </p>
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
        <label className="block text-xs text-slate-500">
          Cover image URL
          <input
            value={coverUrl}
            onChange={(e) => setCoverUrl(e.target.value)}
            placeholder="https://…"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
          />
        </label>
        {coverUrl && (
          <img
            src={coverUrl}
            alt="Cover preview"
            className="mx-auto h-32 rounded-lg object-contain"
          />
        )}
        <label className="block text-xs text-slate-500">
          Total pages
          {enriched?.total_pages ? (
            <span className="ml-1 text-amber-300/80">(check your edition)</span>
          ) : null}
        </label>
        <input
          type="number"
          min={1}
          value={totalPages}
          onChange={(e) => setTotalPages(e.target.value)}
          placeholder="e.g. 180"
          className={`w-full rounded-lg border bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500 ${
            enriched?.total_pages ? "border-amber-700/60" : "border-slate-700"
          }`}
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

interface EditBookCoverProps {
  book: Book;
  onSave: (bookId: number, coverUrl: string | null) => Promise<void>;
}

export function EditBookCover({ book, onSave }: EditBookCoverProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(book.cover_url ?? "");
  const [loading, setLoading] = useState(false);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = () => {
    setValue(book.cover_url ?? "");
    setError(null);
    setEditing(true);
  };

  const cancel = () => {
    setValue(book.cover_url ?? "");
    setError(null);
    setEditing(false);
  };

  const lookup = async () => {
    setLookupLoading(true);
    setError(null);
    try {
      const result = await enrichBook({
        title: book.title,
        author: book.author ?? undefined,
        language: "pl",
        cover_only: true,
      });
      if (result.cover_url) {
        setValue(result.cover_url);
      } else {
        setError("No cover found — paste an image URL manually.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cover lookup failed");
    } finally {
      setLookupLoading(false);
    }
  };

  const save = async () => {
    const trimmed = value.trim();
    if (trimmed && !/^https?:\/\//i.test(trimmed)) {
      setError("Enter a valid http(s) URL");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onSave(book.id, trimmed || null);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update");
    } finally {
      setLoading(false);
    }
  };

  if (!editing) {
    return (
      <button
        type="button"
        onClick={open}
        className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-700 hover:text-violet-300"
      >
        {book.cover_url ? "Edit cover" : "Add cover"}
      </button>
    );
  }

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="https://…"
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs outline-none focus:border-violet-500 sm:min-w-[220px]"
        aria-label="Cover image URL"
      />
      {value && (
        <img src={value} alt="Cover preview" className="h-20 w-14 rounded object-cover" />
      )}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={lookupLoading}
          onClick={lookup}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-violet-300 hover:bg-slate-700 disabled:opacity-50"
        >
          {lookupLoading ? "…" : "✨ Find cover"}
        </button>
        <button
          type="button"
          disabled={loading}
          onClick={save}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "…" : "Save"}
        </button>
        <button
          type="button"
          onClick={cancel}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

interface EditTotalPagesProps {
  book: Book;
  onSave: (bookId: number, totalPages: number) => Promise<void>;
}

export function EditTotalPages({ book, onSave }: EditTotalPagesProps) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(book.total_pages));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = () => {
    setValue(String(book.total_pages));
    setError(null);
    setEditing(true);
  };

  const cancel = () => {
    setValue(String(book.total_pages));
    setError(null);
    setEditing(false);
  };

  const save = async () => {
    const pages = parseInt(value, 10);
    if (!pages || pages < 1) {
      setError("Enter a valid page count");
      return;
    }
    if (pages < book.current_page) {
      setError(`Cannot be less than current page (${book.current_page})`);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onSave(book.id, pages);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update");
    } finally {
      setLoading(false);
    }
  };

  if (!editing) {
    return (
      <button
        type="button"
        onClick={open}
        className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-700 hover:text-violet-300"
      >
        Edit pages
      </button>
    );
  }

  return (
    <div className="flex w-full flex-col gap-2 sm:w-auto">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="number"
          min={book.current_page || 1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-24 rounded-lg border border-amber-700/60 bg-slate-900 px-3 py-1.5 text-xs outline-none focus:border-violet-500"
          aria-label="Total pages"
        />
        <span className="text-xs text-slate-500">pages</span>
        <button
          type="button"
          disabled={loading}
          onClick={save}
          className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "…" : "Save"}
        </button>
        <button
          type="button"
          onClick={cancel}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

interface DeleteBookButtonProps {
  onDelete: () => void;
  compact?: boolean;
}

export function DeleteBookButton({ onDelete, compact }: DeleteBookButtonProps) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div className={`flex items-center gap-2 ${compact ? "" : "w-full"}`}>
        <span className="text-xs text-red-300">Remove?</span>
        <button
          type="button"
          onClick={() => {
            onDelete();
            setConfirming(false);
          }}
          className="rounded-lg bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-500"
        >
          Yes, delete
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs hover:bg-slate-700"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setConfirming(true)}
      className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-400 hover:bg-slate-700 hover:text-red-300"
    >
      Delete
    </button>
  );
}

interface BookCardProps {
  book: Book;
  onActivate: (id: number) => void;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  onUpdatePages: (id: number, totalPages: number) => Promise<void>;
  onUpdateCover: (id: number, coverUrl: string | null) => Promise<void>;
  selected: boolean;
}

export function BookCard({
  book,
  onActivate,
  onSelect,
  onDelete,
  onUpdatePages,
  onUpdateCover,
  selected,
}: BookCardProps) {
  return (
    <div
      className={`rounded-xl border p-4 transition-colors ${
        selected
          ? "border-violet-500 bg-violet-950/30"
          : "border-slate-800 bg-slate-900/50 hover:border-slate-700"
      }`}
    >
      <div className="mb-2 flex gap-3">
        {book.cover_url ? (
          <img
            src={book.cover_url}
            alt=""
            className="h-24 w-16 shrink-0 rounded-md object-cover shadow-sm"
          />
        ) : (
          <div className="flex h-24 w-16 shrink-0 items-center justify-center rounded-md bg-slate-800 text-lg text-slate-600">
            📖
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold leading-snug">{book.title}</h3>
              {book.author && <p className="text-sm text-slate-400">{book.author}</p>}
            </div>
            <div className="flex shrink-0 gap-1">
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
        <EditTotalPages book={book} onSave={onUpdatePages} />
        <EditBookCover book={book} onSave={onUpdateCover} />
        {!book.is_active && book.status !== "COMPLETED" && (
          <button
            onClick={() => onActivate(book.id)}
            className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs hover:bg-violet-500"
          >
            Set active
          </button>
        )}
        <DeleteBookButton onDelete={() => onDelete(book.id)} />
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

interface LogCurrentPageFormProps {
  onSubmit: (currentPage: number) => Promise<void>;
  activeBook: Book;
}

export function LogCurrentPageForm({ onSubmit, activeBook }: LogCurrentPageFormProps) {
  const [page, setPage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const minPage = activeBook.current_page || 0;
  const maxPage = activeBook.total_pages;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const value = parseInt(page, 10);
    if (Number.isNaN(value) || value < 0) return;
    if (value < minPage) {
      setError(`Must be at least page ${minPage}`);
      return;
    }
    if (value > maxPage) {
      setError(`Cannot exceed ${maxPage} pages`);
      return;
    }
    setLoading(true);
    try {
      await onSubmit(value);
      setPage("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to log progress");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="flex gap-2">
        <input
          type="number"
          min={minPage}
          max={maxPage}
          value={page}
          onChange={(e) => {
            setPage(e.target.value);
            setError(null);
          }}
          placeholder={`Current page (${minPage}–${maxPage})`}
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm outline-none focus:border-violet-500"
          aria-label={`Current page for ${activeBook.title}`}
        />
        <button
          type="submit"
          disabled={loading || !page}
          className="rounded-lg bg-violet-600 px-5 py-2 text-sm font-medium hover:bg-violet-500 disabled:opacity-50"
        >
          {loading ? "..." : "Update"}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </form>
  );
}
