import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Card, NoteGrid, Spinner } from "../components/ui";

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl font-bold">{user.section_label}</h1>
          <p className="text-sm text-slate-500">Welcome back, {user.full_name}</p>
        </div>
        <Link to="/upload" className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium">
          + Upload a note
        </Link>
      </div>

      <Link
        to="/leaderboard"
        className="block bg-gradient-to-r from-sky-900 to-sky-700 hover:from-sky-800 hover:to-sky-600 text-white rounded-2xl p-4 mb-8 transition"
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sky-200 text-xs">Your points</p>
            <p className="text-2xl font-bold">{data.points}</p>
          </div>
          <div className="text-right">
            <span className={`text-xs font-semibold rounded-lg px-2.5 py-1 ${data.tier_css}`}>{data.tier}</span>
            <p className="text-sky-200 text-xs mt-1.5">View leaderboard →</p>
          </div>
        </div>
      </Link>

      <h2 className="font-semibold mb-3">Subjects</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-8">
        {data.subjects.length ? (
          data.subjects.map((s) => (
            <Link
              key={s.id}
              to={`/subject/${s.id}`}
              className="bg-white hover:bg-sky-50 ring-1 ring-slate-200 hover:ring-sky-300 rounded-xl p-4 text-center shadow-sm transition"
            >
              <div className="font-semibold text-sm">{s.name}</div>
              <div className="text-xs text-slate-400 mt-1">
                {s.chapters} chapter{s.chapters !== 1 && "s"}
              </div>
            </Link>
          ))
        ) : (
          <Card className="p-8 text-center col-span-full">
            <p className="text-sm text-slate-500">No subjects yet — your teachers will add them.</p>
          </Card>
        )}
      </div>

      <h2 className="font-semibold mb-3">Latest notes in your class</h2>
      <NoteGrid notes={data.recent_notes} empty="No notes yet. Be the first to upload!" />
    </>
  );
}
