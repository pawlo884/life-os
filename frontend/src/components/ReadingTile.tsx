import { useCallback, useEffect, useState } from "react";
import {
  activateBook,
  createBook,
  createWishlistItem,
  deleteBook,
  deleteWishlistItem,
  fetchApi,
  getBookLogs,
  getWishlist,
  logReading,
  moveWishlistToShelf,
  updateBook,
  updateWishlistItem,
  type Book,
  type ReadingLog,
  type ReadingOverview,
  type WishlistBook,
  type CopyStatus,
} from "../api";
import { AddBookForm, BookCard, CopyStatusBadge, DeleteBookButton, EditBookCover, EditBookCopy, EditTotalPages, LogCurrentPageForm, MarkBookReturnedButton, ReadingHistory } from "./Books";
import { AddWishlistForm, WishlistCard } from "./Wishlist";
import { Heatmap } from "./Heatmap";
import { DashboardTile } from "./DashboardTile";

type ReadingTab = "shelf" | "wishlist";

export function ReadingTile() {
  const [books, setBooks] = useState<Book[]>([]);
  const [wishlist, setWishlist] = useState<WishlistBook[]>([]);
  const [overview, setOverview] = useState<ReadingOverview | null>(null);
  const [heatmap, setHeatmap] = useState<Record<string, number>>({});
  const [selectedBookId, setSelectedBookId] = useState<number | null>(null);
  const [logs, setLogs] = useState<ReadingLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [tab, setTab] = useState<ReadingTab>("shelf");

  const load = useCallback(async () => {
    const [b, w, o, h] = await Promise.all([
      fetchApi<Book[]>("/books"),
      getWishlist(),
      fetchApi<ReadingOverview>("/books/overview"),
      fetchApi<Record<string, number>>("/books/heatmap"),
    ]);
    setBooks(b);
    setWishlist(w);
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

  const handleLogCurrentPage = async (currentPage: number) => {
    await logReading(currentPage);
    await load();
    if (selectedBookId) {
      setLogs(await getBookLogs(selectedBookId));
    }
  };

  const handleAddBook = async (data: {
    title: string;
    author: string;
    total_pages: number;
    cover_url?: string | null;
    copy_status?: CopyStatus;
    borrowed_from?: string | null;
  }) => {
    await createBook({
      title: data.title,
      author: data.author || undefined,
      total_pages: data.total_pages,
      cover_url: data.cover_url,
      copy_status: data.copy_status,
      borrowed_from: data.borrowed_from,
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
    try {
      await deleteBook(bookId);
      if (selectedBookId === bookId) {
        setSelectedBookId(null);
      }
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete book");
    }
  };

  const handleUpdatePages = async (bookId: number, totalPages: number) => {
    await updateBook(bookId, { total_pages: totalPages });
    await load();
  };

  const handleUpdateCover = async (bookId: number, coverUrl: string | null) => {
    await updateBook(bookId, { cover_url: coverUrl });
    await load();
  };

  const handleUpdateCopy = async (
    bookId: number,
    data: { copy_status: CopyStatus; borrowed_from: string | null },
  ) => {
    await updateBook(bookId, data);
    await load();
  };

  const handleMarkReturned = async (bookId: number) => {
    const book = books.find((b) => b.id === bookId);
    await updateBook(bookId, {
      copy_status: "NONE",
      borrowed_from: book?.borrowed_from ?? null,
    });
    await load();
  };

  const handleAddWishlist = async (data: {
    title: string;
    author?: string | null;
    note?: string | null;
    cover_url?: string | null;
    source_url?: string | null;
    total_pages?: number | null;
  }) => {
    await createWishlistItem(data);
    await load();
    setTab("wishlist");
    setExpanded(true);
  };

  const handleDeleteWishlist = async (itemId: number) => {
    try {
      await deleteWishlistItem(itemId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to remove item");
    }
  };

  const handleMoveWishlistToShelf = async (itemId: number, totalPages?: number) => {
    await moveWishlistToShelf(itemId, totalPages ? { total_pages: totalPages } : undefined);
    await load();
    setTab("shelf");
  };

  const handleUpdateWishlistNote = async (itemId: number, note: string | null) => {
    await updateWishlistItem(itemId, { note });
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
          <div className="mb-3 flex gap-3">
            {activeBook.cover_url ? (
              <img
                src={activeBook.cover_url}
                alt=""
                className="h-28 w-20 shrink-0 rounded-md object-cover shadow-sm"
              />
            ) : (
              <div className="flex h-28 w-20 shrink-0 items-center justify-center rounded-md bg-slate-800 text-2xl text-slate-600">
                📖
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="mb-1 text-xs text-violet-400">Active book</p>
                  <h3 className="font-semibold">{activeBook.title}</h3>
                  {activeBook.author && (
                    <p className="text-sm text-slate-400">{activeBook.author}</p>
                  )}
                  <div className="mt-2">
                    <CopyStatusBadge book={activeBook} />
                  </div>
                </div>
                <DeleteBookButton
                  compact
                  onDelete={() => handleDelete(activeBook.id)}
                />
              </div>
            </div>
          </div>
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
          <div className="mb-3 flex flex-wrap gap-2">
            <EditTotalPages book={activeBook} onSave={handleUpdatePages} />
            <EditBookCover book={activeBook} onSave={handleUpdateCover} />
            <EditBookCopy book={activeBook} onSave={handleUpdateCopy} />
            <MarkBookReturnedButton book={activeBook} onMarkReturned={handleMarkReturned} />
          </div>
          <LogCurrentPageForm
            onSubmit={handleLogCurrentPage}
            activeBook={activeBook}
          />
        </div>
      ) : books.length > 0 ? (
        <p className="mb-5 text-sm text-amber-300/80">No active book — set one from your shelf.</p>
      ) : null}

      <button
        onClick={() => setExpanded((v) => !v)}
        className="mb-4 text-sm text-slate-400 hover:text-slate-200"
      >
        {expanded ? "▾ Hide details" : "▸ Show shelf, wishlist & heatmap"}
      </button>

      {expanded && (
        <>
          <div className="mb-4 flex gap-2">
            <button
              type="button"
              onClick={() => setTab("shelf")}
              className={`rounded-lg px-4 py-2 text-sm ${
                tab === "shelf"
                  ? "bg-violet-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              My shelf ({books.length})
            </button>
            <button
              type="button"
              onClick={() => setTab("wishlist")}
              className={`rounded-lg px-4 py-2 text-sm ${
                tab === "wishlist"
                  ? "bg-amber-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              To buy ({wishlist.length})
            </button>
          </div>

          {tab === "shelf" ? (
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
                    onUpdatePages={handleUpdatePages}
                    onUpdateCover={handleUpdateCover}
                    onUpdateCopy={handleUpdateCopy}
                    onMarkReturned={handleMarkReturned}
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
          ) : (
            <>
              <div className="mb-4">
                <AddWishlistForm onSubmit={handleAddWishlist} />
              </div>
              <div className="mb-5 grid gap-3 sm:grid-cols-2">
                {wishlist.map((item) => (
                  <WishlistCard
                    key={item.id}
                    item={item}
                    onDelete={handleDeleteWishlist}
                    onMoveToShelf={handleMoveWishlistToShelf}
                    onUpdateNote={handleUpdateWishlistNote}
                  />
                ))}
              </div>
              {wishlist.length === 0 && (
                <p className="mb-5 text-center text-sm text-slate-500">
                  Nothing on the list yet — add a title, link or screenshot.
                </p>
              )}
            </>
          )}
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
