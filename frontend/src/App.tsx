import { useEffect, useState } from "react";
import {
  fetchApi,
  type DailyReport,
  type JobApplication,
  type LearningProgress,
  type StreakInfo,
  type WeeklyJobStats,
} from "./api";
import { Heatmap } from "./components/Heatmap";
import { Kanban } from "./components/Kanban";
import { ProgressBars } from "./components/ProgressBars";

export default function App() {
  const [report, setReport] = useState<DailyReport | null>(null);
  const [streak, setStreak] = useState<StreakInfo | null>(null);
  const [heatmap, setHeatmap] = useState<Record<string, number>>({});
  const [jobs, setJobs] = useState<JobApplication[]>([]);
  const [learning, setLearning] = useState<LearningProgress[]>([]);
  const [jobStats, setJobStats] = useState<WeeklyJobStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchApi<DailyReport>("/report/daily"),
      fetchApi<StreakInfo>("/fitness/streak"),
      fetchApi<Record<string, number>>("/fitness/heatmap"),
      fetchApi<JobApplication[]>("/jobs"),
      fetchApi<LearningProgress[]>("/learning"),
      fetchApi<WeeklyJobStats>("/jobs/stats/weekly"),
    ])
      .then(([r, s, h, j, l, js]) => {
        setReport(r);
        setStreak(s);
        setHeatmap(h);
        setJobs(j);
        setLearning(l);
        setJobStats(js);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-7xl p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Life OS</h1>
        <p className="text-slate-400">Personal assistant — command center</p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-800 bg-red-950/50 p-4 text-red-300">
          Failed to connect to API: {error}
        </div>
      )}

      <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Workout streak"
          value={streak ? `${streak.current_streak} days` : "—"}
          alert={streak?.at_risk}
        />
        <StatCard
          label="Applications today"
          value={report ? String(report.applications_sent_today) : "—"}
        />
        <StatCard
          label="Weekly KPI"
          value={jobStats ? `${jobStats.applications_sent}/${jobStats.kpi_target}` : "—"}
          alert={jobStats ? !jobStats.kpi_met : false}
        />
        <StatCard
          label="Book pages remaining"
          value={
            report?.remaining_book_pages != null
              ? String(report.remaining_book_pages)
              : "—"
          }
        />
      </section>

      <section className="mb-8 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold">Workout heatmap</h2>
        <Heatmap data={heatmap} />
      </section>

      <section className="mb-8 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold">Learning & growth</h2>
        <ProgressBars items={learning} />
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <h2 className="mb-4 text-lg font-semibold">Job hunt pipeline</h2>
        <Kanban jobs={jobs} />
      </section>
    </div>
  );
}

function StatCard({
  label,
  value,
  alert,
}: {
  label: string;
  value: string;
  alert?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        alert ? "border-amber-700 bg-amber-950/30" : "border-slate-800 bg-slate-900/50"
      }`}
    >
      <p className="text-sm text-slate-400">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
