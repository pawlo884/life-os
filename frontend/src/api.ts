export interface BookEnrichment {
  title: string;
  author: string | null;
  total_pages: number | null;
  cover_url: string | null;
  language: string | null;
  source: string;
  confidence: string;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: isFormData
      ? options?.headers
      : { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg).join(", ")
      : typeof detail === "string"
        ? detail.replace(/\s+/g, " ").trim()
        : detail
          ? String(detail)
          : `API error: ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export interface Book {
  id: number;
  title: string;
  author: string | null;
  total_pages: number;
  current_page: number;
  status: string;
  is_active: boolean;
  completion_percent: number;
  remaining_pages: number;
  avg_pages_per_day: number | null;
  estimated_completion_date: string | null;
}

export interface ReadingLog {
  id: number;
  book_id: number;
  pages_read: number;
  log_date: string;
  note: string | null;
}

export interface ReadingOverview {
  pages_today: number;
  pages_this_week: number;
  active_book: Book | null;
  books_reading: number;
  books_completed: number;
}

export interface ReadingSessionResult {
  book: Book;
  pages_logged: number;
  log_date: string;
}

export async function createBook(data: {
  title: string;
  author?: string;
  total_pages: number;
  current_page?: number;
  is_active?: boolean;
}): Promise<Book> {
  return fetchApi<Book>("/books", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function logReading(pages: number, bookId?: number): Promise<ReadingSessionResult> {
  return fetchApi<ReadingSessionResult>("/books/read", {
    method: "POST",
    body: JSON.stringify({ pages, book_id: bookId }),
  });
}

export async function activateBook(bookId: number): Promise<Book> {
  return fetchApi<Book>(`/books/${bookId}/activate`, { method: "POST" });
}

export async function getBookLogs(bookId: number): Promise<ReadingLog[]> {
  return fetchApi<ReadingLog[]>(`/books/${bookId}/logs`);
}

export async function deleteBook(bookId: number): Promise<void> {
  await fetchApi<void>(`/books/${bookId}`, { method: "DELETE" });
}

export async function updateBook(
  bookId: number,
  data: {
    title?: string;
    author?: string | null;
    total_pages?: number;
    current_page?: number;
    status?: string;
    is_active?: boolean;
  },
): Promise<Book> {
  return fetchApi<Book>(`/books/${bookId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function enrichBook(input: {
  title?: string;
  url?: string;
  image?: File;
  language?: string;
}): Promise<BookEnrichment> {
  const form = new FormData();
  if (input.title) form.append("title", input.title);
  if (input.url) form.append("url", input.url);
  if (input.image) form.append("image", input.image);
  if (input.language) form.append("language", input.language);
  return fetchApi<BookEnrichment>("/books/enrich", { method: "POST", body: form });
}
