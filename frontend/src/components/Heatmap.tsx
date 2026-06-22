interface HeatmapProps {
  data: Record<string, number>;
  unit?: string;
}

export function Heatmap({ data, unit = "pages" }: HeatmapProps) {
  const today = new Date();
  const cells: { date: string; count: number }[] = [];

  for (let i = 364; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    cells.push({ date: key, count: data[key] || 0 });
  }

  const max = Math.max(...cells.map((c) => c.count), 1);

  const level = (count: number) => {
    if (count === 0) return "bg-slate-800";
    const ratio = count / max;
    if (ratio <= 0.25) return "bg-violet-900";
    if (ratio <= 0.5) return "bg-violet-700";
    if (ratio <= 0.75) return "bg-violet-500";
    return "bg-violet-300";
  };

  return (
    <div className="grid grid-flow-col grid-rows-7 gap-1 overflow-x-auto">
      {cells.map((cell) => (
        <div
          key={cell.date}
          title={`${cell.date}: ${cell.count} ${unit}`}
          className={`h-3 w-3 rounded-sm ${level(cell.count)}`}
        />
      ))}
    </div>
  );
}
