import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Card, Spinner } from "../components/ui";

const MEDALS = ["🥇", "🥈", "🥉"];

export default function Leaderboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/leaderboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <h1 className="text-xl font-bold mb-1">Leaderboard — {data.section_label}</h1>
      <p className="text-sm text-slate-500 mb-6">
        Top contributors this term. Upload notes (+10), earn upvotes (+2) and downloads (+1).
      </p>

      {user.role === "student" && (
        <div className="bg-gradient-to-r from-sky-900 to-sky-700 text-white rounded-2xl p-5 mb-6 flex items-center justify-between">
          <div>
            <p className="text-sky-200 text-sm">Your points</p>
            <p className="text-3xl font-bold">{data.my_points}</p>
          </div>
          <span className={`text-sm font-semibold rounded-lg px-3 py-1.5 ${data.my_tier_css}`}>{data.my_tier}</span>
        </div>
      )}

      <Card className="overflow-hidden">
        {data.rows.length ? (
          data.rows.map((row, i) => (
            <div
              key={row.id}
              className={`flex items-center gap-4 px-5 py-3 ${row.id === user.id ? "bg-sky-50" : ""} ${i > 0 ? "border-t border-slate-100" : ""}`}
            >
              <span className="w-8 text-center font-bold text-lg text-slate-300">
                {i < 3 ? MEDALS[i] : i + 1}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm truncate">
                  {row.full_name}
                  {row.id === user.id && <span className="text-sky-600 text-xs"> (you)</span>}
                </p>
                <p className="text-xs text-slate-400 font-mono">{row.login_id}</p>
              </div>
              <span className={`text-[10px] uppercase font-bold rounded-md px-1.5 py-0.5 ${row.tier_css}`}>{row.tier}</span>
              <span className="font-bold text-slate-700 w-14 text-right">{row.points}</span>
            </div>
          ))
        ) : (
          <p className="px-5 py-10 text-center text-sm text-slate-400">
            No points earned yet — upload the first note to take the lead!
          </p>
        )}
      </Card>
    </>
  );
}
