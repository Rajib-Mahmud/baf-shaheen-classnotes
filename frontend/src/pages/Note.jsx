import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Alert, Badge, Breadcrumb, Button, Card, Field, Spinner, inputCls } from "../components/ui";

function Lightbox({ images, index, onClose, onNav }) {
  const handleKey = useCallback(
    (e) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft") onNav(-1);
      if (e.key === "ArrowRight") onNav(1);
    },
    [onClose, onNav]
  );
  useEffect(() => {
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [handleKey]);
  const [startX, setStartX] = useState(null);
  return (
    <div
      className="fixed inset-0 z-50 bg-black/95 flex flex-col"
      onTouchStart={(e) => setStartX(e.touches[0].clientX)}
      onTouchEnd={(e) => {
        if (startX === null) return;
        const dx = e.changedTouches[0].clientX - startX;
        if (Math.abs(dx) > 50) onNav(dx < 0 ? 1 : -1);
        setStartX(null);
      }}
    >
      <div className="flex items-center justify-between px-4 py-3 text-white text-sm shrink-0">
        <span>
          Page {index + 1} of {images.length}
        </span>
        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg text-2xl leading-none">
          &times;
        </button>
      </div>
      <div className="flex-1 min-h-0 flex items-center justify-center relative px-2 pb-4">
        <button onClick={() => onNav(-1)} className="absolute left-2 z-10 text-white bg-white/10 hover:bg-white/20 rounded-full w-10 h-10 text-xl">
          ‹
        </button>
        <img src={`/image/${images[index].id}`} alt="" className="max-h-full max-w-full object-contain select-none" />
        <button onClick={() => onNav(1)} className="absolute right-2 z-10 text-white bg-white/10 hover:bg-white/20 rounded-full w-10 h-10 text-xl">
          ›
        </button>
      </div>
    </div>
  );
}

export default function Note() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [note, setNote] = useState(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [lightbox, setLightbox] = useState(null);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState("wrong_info");
  const [comment, setComment] = useState("");

  const load = useCallback(() => {
    api.get(`/note/${id}`).then((n) => {
      setNote(n);
      setTitle(n.title);
      setDescription(n.description || "");
    }).catch((e) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <p className="text-red-600 text-sm">{error}</p>;
  if (!note) return <Spinner />;

  const act = (fn) => fn().then(load).catch((e) => setError(e.message));

  const doVote = () => act(() => api.post(`/note/${id}/vote`));
  const doDelete = () => {
    if (!confirm("Delete this note and all its photos?")) return;
    api.del(`/note/${id}`).then((d) => navigate(`/chapter/${d.chapter_id}`)).catch((e) => setError(e.message));
  };
  const doUnhide = () => act(() => api.post(`/teacher/note/${id}/unhide`));
  const saveEdit = (e) => {
    e.preventDefault();
    act(() => api.put(`/note/${id}`, { title, description })).then(() => setEditing(false));
  };
  const submitReport = (e) => {
    e.preventDefault();
    api.post(`/note/${id}/report`, { reason, comment })
      .then(() => {
        setReporting(false);
        setFlash("Report submitted. Your class teacher will review it.");
        load();
      })
      .catch((e2) => setError(e2.message));
  };

  return (
    <>
      <Breadcrumb
        items={[
          [note.subject_name, `/subject/${note.subject_id}`],
          [note.chapter_title, `/chapter/${note.chapter_id}`],
          [note.title, null],
        ]}
      />

      {note.is_hidden && (
        <div className="mb-4 rounded-lg bg-amber-50 border border-amber-300 text-amber-900 px-4 py-3 text-sm flex flex-wrap items-center justify-between gap-2">
          <span>⚠ This note is <b>hidden from students</b> (moderation).</span>
          {note.is_moderator && (
            <Button kind="warn" onClick={doUnhide}>Unhide</Button>
          )}
        </div>
      )}

      <Alert kind="success" onClose={() => setFlash("")}>{flash}</Alert>
      <Alert onClose={() => setError("")}>{error}</Alert>

      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div>
          <h1 className="text-xl font-bold leading-tight">{note.title}</h1>
          <p className="text-sm text-slate-500 mt-1 flex flex-wrap items-center gap-1.5">
            {note.is_official ? <Badge kind="official">★ Official</Badge> : <Badge kind="student">Student note</Badge>}
            <span>
              by <span className="font-medium text-slate-700">{note.uploader}</span>
            </span>
            <span>· {note.created_at_full}</span>
            <span>· {note.pages} page{note.pages !== 1 && "s"}</span>
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <button
            onClick={doVote}
            disabled={note.uploader_id === undefined}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              note.my_vote
                ? "bg-sky-800 text-white hover:bg-sky-700"
                : "bg-white ring-1 ring-slate-300 hover:bg-sky-50 text-slate-700"
            }`}
          >
            ▲ {note.votes}
          </button>
          {note.can_manage && (
            <>
              <Button kind="ghost" onClick={() => setEditing(!editing)}>Edit</Button>
              <Button kind="danger" onClick={doDelete}>Delete</Button>
            </>
          )}
        </div>
      </div>

      {editing && (
        <Card className="p-4 mb-4 max-w-md">
          <form onSubmit={saveEdit}>
            <Field label="Title">
              <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="Description (optional)">
              <textarea className={inputCls} rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
            </Field>
            <Button type="submit">Save changes</Button>
          </form>
        </Card>
      )}

      {note.description && !editing && (
        <p className="text-sm text-slate-600 mb-4 whitespace-pre-line bg-white rounded-lg ring-1 ring-slate-200 px-4 py-3">
          {note.description}
        </p>
      )}

      <div className="space-y-5 mt-5">
        {note.images.map((img, i) => (
          <Card key={img.id} className="p-3">
            <img
              src={`/image/${img.id}`}
              alt={`${note.title} — page ${i + 1}`}
              loading="lazy"
              className="w-full rounded-lg cursor-zoom-in"
              onClick={() => setLightbox(i)}
            />
            <div className="flex items-center justify-between mt-2 text-sm px-1">
              <span className="text-slate-400 text-xs">
                Page {i + 1} of {note.images.length} · tap photo to zoom
              </span>
              <a href={`/image/${img.id}?download=1`} className="text-sky-700 hover:underline font-medium">
                Download
              </a>
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-8">
        {note.already_reported ? (
          <p className="text-xs text-slate-400">You reported this note — a teacher will review it.</p>
        ) : (
          <>
            <button onClick={() => setReporting(!reporting)} className="text-xs text-slate-400 hover:text-red-600">
              ⚑ Report a problem with this note
            </button>
            {reporting && (
              <Card className="mt-3 p-4 max-w-md">
                <form onSubmit={submitReport}>
                  <Field label="Reason">
                    <select className={inputCls} value={reason} onChange={(e) => setReason(e.target.value)}>
                      {Object.entries(note.report_reasons).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Details (optional)">
                    <textarea className={inputCls} rows={2} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="What's wrong?" />
                  </Field>
                  <Button kind="danger" type="submit">Submit report</Button>
                </form>
              </Card>
            )}
          </>
        )}
      </div>

      {lightbox !== null && (
        <Lightbox
          images={note.images}
          index={lightbox}
          onClose={() => setLightbox(null)}
          onNav={(d) => setLightbox((i) => (i + d + note.images.length) % note.images.length)}
        />
      )}
    </>
  );
}
