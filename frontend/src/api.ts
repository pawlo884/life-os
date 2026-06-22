const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export interface DailyReport {
  date: string;
  applications_sent_today: number;
  fitness_streak_days: number;
  streak_at_risk: boolean;
  active_book: string | null;
  remaining_book_pages: number | null;
}

export interface StreakInfo {
  current_streak: number;
  last_activity_date: string | null;
  at_risk: boolean;
}

export interface JobApplication {
  id: number;
  company: string;
  role: string;
  status: string;
  tech_stack: string | null;
  notes: string | null;
  applied_date: string | null;
}

export interface LearningProgress {
  id: number;
  resource_type: string;
  title: string;
  total_units: number;
  completed_units: number;
  status: string;
  completion_percent: number;
}

export interface WeeklyJobStats {
  week_start: string;
  applications_sent: number;
  kpi_target: number;
  kpi_met: boolean;
}
