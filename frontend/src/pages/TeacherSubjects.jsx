import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card, Spinner } from "../components/ui";

export default function TeacherSubjects() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/teacher/subjects").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <h1 className="text-xl font-bold mb-6">My subjects</h1>
      {data.subjects.length ? (
        <div className="grid sm:grid-cols-2 gap-4">
          {data.subjects.map((s) => (
            <Card key={s.id} className="p-5">
              <h2 className="font-semibold">{s.name}</h2>
              <p className="text-sm text-slate-500 mb-3">
                {s.section_label} · {s.chapters} chapter{s.chapters !== 1 && "s"}
              </p>
              <div className="flex gap-3 text-sm">
                <Link to={`/teacher/subject/${s.id}`} className="text-sky-700 hover:underline">
                  Manage chapters
                </Link>
                <Link to={`/subject/${s.id}`} className="text-sky-700 hover:underline">
                  View notes
                </Link>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <p className="text-slate-500">No subjects assigned to you yet. Ask the admin.</p>
      )}
    </>
  );
}
