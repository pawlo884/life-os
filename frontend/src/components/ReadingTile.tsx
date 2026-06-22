import { useCallback, useEffect, useState } from "react";
import {
  activateBook,
  createBook,
  deleteBook,
  fetchApi,
  getBookLogs,
  logReading,
  type Book,
  type ReadingLog,
  type ReadingOverview,
} from "../api";
import { AddBookForm, BookCard, LogPagesForm, ReadingHistory } from "./Books";
import { Heatmap } from "./Heatmap";
import { DashboardTile } from "./DashboardTile";

export function ReadingTile() {
  const [books, setBooks] = useState<Book[]>([]);
  const [overview, setOverview] = useState<ReadingOverview | null>(null);
  const [heatmap, setHeatmap] = useState<Record<string, number>>({});
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null);
  const [logs, setLogs] = useState<ReadingLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const load = useCallback(async () => {
    const [b, o, h] = await Promise.all([
      fetchApi<Book[]>("/books"),
      fetchApi<ReadingOverview>("/books/overview"),
      fetchApi<Record<string, number>>("/books/heatmap"),
    ]);
    setBooks(b);
    setOverview(o);
    setHeatmap(h);
    setError(null);
  }, []);

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, [load]);

  useEffect(() => {
    if (!selectedBookId) {
      setLogs([]);
      return;
    }
    getBookLogs(selectedBookId)
      .then(setLogs)
      .catch((e) => setError(e.message));
  }, [selectedBookId]);

  const handleLogPages = async (pages: number) => {
    await logReading(pages);
    await load();
    if (selectedBookId) {
      setLogs(await getBookLogs(selectedBookId));
    }
  };

  const handleAddBook = async (data: { title: string; author: string; total_pages: number }) => {
    await createBook({
      title: data.title,
      author: data.author || undefined,
      total_pages: data.total_pages,
      is_active: books.length === 0,
    });
    await load();
    setExpanded(true);
  };

  const handleActivate = async (bookId: number) => {
    await activateBook(bookId);
    await load();
  };

  const handleDelete = async (bookId: number) => {
    await deleteBook(bookId);
    if (selectedBookId === bookId) {
      setSelectedBookId(null);
    }
    await load();
  };

  const activeBook = overview?.active_book;
  const selectedBook = books.find((b) => b.id === selectedBookId);

  return (
    <DashboardTile title="Reading" subtitle="Books & pages" accent="violet" span="wide">
      {error && (
        <div className="mb-4 rounded-lg border border-red-800 bg-red-950/50 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <MiniStat label="Today" value={overview ? String(overview.pages_today) : "—"} />
        <MiniStat label="This week" value={overview ? String(overview.pages_this_week) : "—"} />
        <MiniStat label="On shelf" value={overview ? String(overview.books_reading) : "—"} />
      </div>

      {activeBook ? (
        <div className="mb-5 rounded-lg border border-violet-800/30 bg-violet-950/20 p-4">
          <p className="mb-1 text-xs text-violet-400">Active book</p>
          <h3 className="mb-1 font-semibold">{activeBook.title}</h3>
          {activeBook.author && (
            <p className="mb-3 text-sm text-slate-400">{activeBook.author}</p>
          )}
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-slate-400">
              {activeBook.remaining_pages} left · {activeBook.current_page}/{activeBook.total_pages}
            </span>
            <span className="text-violet-400">{activeBook.completion_percent}%</span>
          </div>
          <div className="mb-3 h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-violet-500"
              style={{ width: `${activeBook.completion_percent}%` }}
            />
          </div>
          {activeBook.estimated_completion_date && (
            <p className="mb-3 text-xs text-slate-500">
              Est. {activeBook.estimated_completion_date}
              {activeBook.avg_pages_per_day ? ` · ${activeBook.avg_pages_per_day} ppd` : ""}
            </p>
          )}
          <LogPagesForm onSubmit={handleLogPages} activeBookTitle={activeBook.title} />
        </div>
      ) : books.length > 0 ? (
        <p className="mb-5 text-sm text-amber-300/80">No active book — set one from your shelf.</p>
      ) : null}

      <button
        onClick={() => setExpanded((v) => !v)}
        className="mb-4 text-sm text-slate-400 hover:text-slate-200"
      >
        {expanded ? "▾ Hide shelf" : "▸ Show shelf & heatmap"}
      </button>

      {expanded && (
        <>
          <div className="mb-4">
            <AddBookForm onSubmit={handleAddBook} />
          </div>
          <div className="mb-5 grid gap-3 sm:grid-cols-2">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                onActivate={handleActivate}
                onSelect={setSelectedBookId}
                onDelete={handleDelete}
                selected={selectedBookId === book.id}
              />
            ))}
          </div>
          {books.length === 0 && (
            <p className="mb-5 text-center text-sm text-slate-500">Add your first book above.</p>
          )}
          {selectedBook && (
            <div className="mb-5">
              <h4 className="mb-2 text-sm font-medium text-slate-300">
                History — {selectedBook.title}
              </h4>
              <ReadingHistory logs={logs} bookTitle={selectedBook.title} />
            </div>
          )}
          <Heatmap data={heatmap} unit="pages" />
        </>
      )}
    </DashboardTile>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-800/50 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-bold">{value}</p>
    </div>
  );
}
