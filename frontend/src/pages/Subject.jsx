import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Breadcrumb, Card, Spinner } from "../components/ui";

export default function Subject() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/subject/${id}`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <Breadcrumb items={[["Home", "/"], [data.name, null]]} />
      <h1 className="text-xl font-bold mb-1">{data.name}</h1>
      <p className="text-sm text-slate-500 mb-6">
        {data.section_label}
        {data.teacher && (
          <>
            {" "}· Teacher: <span className="font-medium text-slate-700">{data.teacher}</span>
          </>
        )}
      </p>

      <Card className="divide-y divide-slate-100 overflow-hidden">
        {data.chapters.length ? (
          data.chapters.map((ch, i) => (
            <Link
              key={ch.id}
              to={`/chapter/${ch.id}`}
              className="flex items-center justify-between px-5 py-3.5 hover:bg-sky-50 transition group"
            >
              <span className="flex items-center gap-3">
                <span className="bg-slate-100 group-hover:bg-sky-100 text-slate-500 group-hover:text-sky-700 rounded-lg w-8 h-8 grid place-items-center text-xs font-bold transition">
                  {i + 1}
                </span>
                <span className="font-medium text-sm">{ch.title}</span>
              </span>
              <span className="text-xs text-slate-400 whitespace-nowrap">
                {ch.notes} note{ch.notes !== 1 && "s"} →
              </span>
            </Link>
          ))
        ) : (
          <p className="px-5 py-8 text-sm text-slate-400 text-center">No chapters yet — your teacher will add them.</p>
        )}
      </Card>
    </>
  );
}
