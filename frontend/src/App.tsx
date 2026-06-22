import { DashboardTile } from "./components/DashboardTile";
import { ReadingTile } from "./components/ReadingTile";

const PLACEHOLDER_TILES = [
  { title: "Workouts", subtitle: "Strava & streaks", accent: "emerald" as const },
  { title: "Job hunt", subtitle: "Applications pipeline", accent: "amber" as const },
  { title: "Learning", subtitle: "Courses & modules", accent: "sky" as const },
];

export default function App() {
  return (
    <div className="mx-auto max-w-7xl p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Life OS</h1>
        <p className="text-slate-400">Personal command center</p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 lg:grid-rows-2">
        <ReadingTile />

        {PLACEHOLDER_TILES.map((tile) => (
          <DashboardTile
            key={tile.title}
            title={tile.title}
            subtitle={tile.subtitle}
            accent={tile.accent}
            comingSoon
          >
            <p className="text-sm text-slate-500">Module coming in a future release.</p>
          </DashboardTile>
        ))}
      </div>
    </div>
  );
}
