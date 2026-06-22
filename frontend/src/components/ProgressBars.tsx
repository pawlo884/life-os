import type { LearningProgress } from "../api";

interface ProgressBarsProps {
  items: LearningProgress[];
}

export function ProgressBars({ items }: ProgressBarsProps) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.id}>
          <div className="mb-1 flex justify-between text-sm">
            <span>
              {item.title}{" "}
              <span className="text-slate-500">({item.resource_type})</span>
            </span>
            <span className="text-emerald-400">{item.completion_percent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${item.completion_percent}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
