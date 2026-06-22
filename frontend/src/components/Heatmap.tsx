interface HeatmapProps {
  data: Record<string, number>;
}

export function Heatmap({ data }: HeatmapProps) {
  const today = new Date();
  const cells: { date: string; count: number }[] = [];

  for (let i = 364; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    cells.push({ date: key, count: data[key] || 0 });
  }

  const level = (count: number) => {
    if (count === 0) return "bg-slate-800";
    if (count === 1) return "bg-emerald-900";
    if (count === 2) return "bg-emerald-700";
    return "bg-emerald-500";
  };

  return (
    <div className="grid grid-flow-col grid-rows-7 gap-1 overflow-x-auto">
      {cells.map((cell) => (
        <div
          key={cell.date}
          title={`${cell.date}: ${cell.count} workout(s)`}
          className={`h-3 w-3 rounded-sm ${level(cell.count)}`}
        />
      ))}
    </div>
  );
}
