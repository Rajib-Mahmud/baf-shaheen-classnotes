import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Breadcrumb, Card, NoteCard, Spinner } from "../components/ui";

export default function Chapter() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    api.get(`/chapter/${id}`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  const official = data.notes.filter((n) => n.is_official).length;
  const visible = data.notes.filter(
    (n) => filter === "all" || (filter === "official" ? n.is_official : !n.is_official)
  );

  const tabs = [
    ["all", `All (${data.notes.length})`],
    ["official", `★ Official (${official})`],
    ["student", `Student (${data.notes.length - official})`],
  ];

  return (
    <>
      <Breadcrumb items={[[data.subject.name, `/subject/${data.subject.id}`], [data.title, null]]} />
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <h1 className="text-xl font-bold">{data.title}</h1>
        {data.can_upload && (
          <Link
            to={`/upload?chapter=${data.id}`}
            className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg px-4 py-2 text-sm font-medium"
          >
            + Upload here
          </Link>
        )}
      </div>

      {data.notes.length > 0 && (
        <div className="flex gap-2 mb-4 text-sm">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-lg ${
                filter === key ? "bg-sky-800 text-white" : "bg-white ring-1 ring-slate-200 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {visible.length ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {visible.map((n) => (
            <NoteCard key={n.id} note={n} />
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <p className="text-sm text-slate-500 mb-2">
            {data.notes.length ? "No notes of this type yet." : "No notes in this chapter yet."}
          </p>
          {data.can_upload && !data.notes.length && (
            <Link to={`/upload?chapter=${data.id}`} className="text-sky-700 font-medium text-sm hover:underline">
              Be the first to upload →
            </Link>
          )}
        </Card>
      )}
    </>
  );
}
