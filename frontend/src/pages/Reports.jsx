import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, Badge, Button, Card, Spinner } from "../components/ui";

export default function Reports() {
  const [show, setShow] = useState("open");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setData(null);
    api.get(`/teacher/reports?show=${show}`).then(setData).catch((e) => setError(e.message));
  }, [show]);
  useEffect(load, [load]);

  const act = (path) => api.post(path).then(load).catch((e) => setError(e.message));

  if (error && !data) return <p className="text-red-600 text-sm">{error}</p>;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h1 className="text-xl font-bold">Reported notes</h1>
        <div className="flex gap-2 text-sm">
          {["open", "all"].map((key) => (
            <button
              key={key}
              onClick={() => setShow(key)}
              className={`px-3 py-1.5 rounded-lg capitalize ${
                show === key ? "bg-sky-800 text-white" : "bg-white ring-1 ring-slate-200"
              }`}
            >
              {key}
            </button>
          ))}
        </div>
      </div>
      <Alert onClose={() => setError("")}>{error}</Alert>

      {!data ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          {data.reports.length ? (
            data.reports.map((r) => (
              <Card key={r.id} className={`p-4 ${r.status === "resolved" ? "opacity-60" : ""}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span
                        className={`text-[10px] uppercase font-bold rounded-md px-1.5 py-0.5 ${
                          r.reason === "inappropriate"
                            ? "bg-red-100 text-red-700"
                            : r.reason === "wrong_info"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {r.reason_label}
                      </span>
                      {r.status === "resolved" && (
                        <span className="text-[10px] uppercase font-bold bg-emerald-100 text-emerald-700 rounded-md px-1.5 py-0.5">
                          Resolved
                        </span>
                      )}
                      {r.note.is_hidden && <Badge kind="hidden">Note hidden</Badge>}
                    </div>
                    <Link to={`/note/${r.note.id}`} className="font-medium text-sm text-sky-800 hover:underline">
                      {r.note.title}
                    </Link>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {r.note_section} · {r.note_subject} · uploaded by {r.note.uploader}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      Reported by <b>{r.reporter}</b> · {r.created_at} UTC
                    </p>
                    {r.comment && (
                      <p className="text-sm text-slate-600 mt-1.5 bg-slate-50 rounded-lg px-3 py-2">"{r.comment}"</p>
                    )}
                  </div>
                  {r.status === "open" && (
                    <div className="flex flex-wrap gap-2 shrink-0">
                      {!r.note.is_hidden && (
                        <Button kind="warn" className="!px-3 !py-1.5 !text-xs" onClick={() => act(`/teacher/reports/${r.id}/hide-note`)}>
                          Hide note
                        </Button>
                      )}
                      <Button
                        kind="danger"
                        className="!px-3 !py-1.5 !text-xs"
                        onClick={() => confirm("Permanently delete this note and its photos?") && act(`/teacher/reports/${r.id}/delete-note`)}
                      >
                        Delete note
                      </Button>
                      <Button kind="ghost" className="!px-3 !py-1.5 !text-xs" onClick={() => act(`/teacher/reports/${r.id}/dismiss`)}>
                        Dismiss
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            ))
          ) : (
            <Card className="p-10 text-center">
              <p className="text-sm text-slate-400">No {show === "open" ? "open " : ""}reports. 🎉</p>
            </Card>
          )}
        </div>
      )}
    </>
  );
}
