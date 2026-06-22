import type { JobApplication } from "../api";

const COLUMNS = [
  { key: "to_apply", label: "To apply" },
  { key: "applied", label: "Applied" },
  { key: "hr_interview", label: "HR interview" },
  { key: "tech_interview", label: "Tech interview" },
  { key: "take_home", label: "Take-home" },
  { key: "rejected", label: "Rejected" },
  { key: "offer", label: "Offer" },
];

interface KanbanProps {
  jobs: JobApplication[];
}

export function Kanban({ jobs }: KanbanProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-7">
      {COLUMNS.map((col) => (
        <div key={col.key} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
          <h3 className="mb-3 text-sm font-semibold text-slate-300">{col.label}</h3>
          <div className="space-y-2">
            {jobs
              .filter((j) => j.status === col.key)
              .map((job) => (
                <div key={job.id} className="rounded-lg bg-slate-800 p-3 text-sm">
                  <p className="font-medium">{job.company}</p>
                  <p className="text-slate-400">{job.role}</p>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
