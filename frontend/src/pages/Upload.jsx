import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Alert, Card, Field, Spinner, inputCls } from "../components/ui";

const MAX_FILES = 10;
const MAX_SIZE = 8 * 1024 * 1024;
const OK_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function Upload() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [chapters, setChapters] = useState(null);
  const [chapterId, setChapterId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef();

  useEffect(() => {
    api.get("/upload-targets").then((d) => {
      setChapters(d.chapters);
      const pre = params.get("chapter");
      if (pre && d.chapters.some((c) => String(c.id) === pre)) setChapterId(pre);
      else if (d.chapters.length) setChapterId(String(d.chapters[0].id));
    }).catch((e) => setError(e.message));
  }, [params]);

  if (!chapters) return <Spinner />;
  if (!chapters.length)
    return <Card className="p-8 text-center text-sm text-slate-500">No chapters available to upload into yet.</Card>;

  const fileProblem = (f) =>
    !OK_TYPES.includes(f.type) ? "wrong type" : f.size > MAX_SIZE ? "over 8 MB" : null;

  const addFiles = (list) => {
    setFiles((prev) => [...prev, ...Array.from(list)].slice(0, MAX_FILES + 5));
    setError("");
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return setError("Title is required.");
    if (!files.length) return setError("Choose at least one photo.");
    if (files.length > MAX_FILES) return setError(`At most ${MAX_FILES} photos per note.`);
    if (files.some(fileProblem)) return setError("Fix the highlighted photos first.");
    setBusy(true);
    const fd = new FormData();
    fd.append("chapter_id", chapterId);
    fd.append("title", title.trim());
    fd.append("description", description.trim());
    files.forEach((f) => fd.append("images", f));
    try {
      const data = await api.postForm("/upload", fd);
      navigate(`/note/${data.note_id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto">
      <Card className="p-6">
        <h1 className="text-lg font-bold mb-1">Upload note photos</h1>
        <p className="text-sm text-slate-500 mb-5">Snap clear photos of the notes — one note can hold several pages.</p>
        <Alert onClose={() => setError("")}>{error}</Alert>
        <form onSubmit={submit}>
          <Field label="Chapter">
            <select className={inputCls} value={chapterId} onChange={(e) => setChapterId(e.target.value)}>
              {chapters.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Title">
            <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Vectors — board work 12 Aug" maxLength={160} />
          </Field>
          <Field label="Description (optional)">
            <textarea className={inputCls} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Anything your classmates should know" maxLength={2000} />
          </Field>

          <Field label="Note photos">
            <button
              type="button"
              onClick={() => inputRef.current.click()}
              className="w-full border-2 border-dashed border-slate-300 hover:border-sky-400 rounded-xl p-6 text-center transition"
            >
              <span className="text-sm text-slate-600 font-medium block">Tap to choose photos or use the camera</span>
              <span className="block text-xs text-slate-400 mt-1">Up to 10 photos · max 8 MB each · JPG, PNG, WebP</span>
            </button>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
            />
          </Field>

          {files.length > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 mb-4">
              {files.map((f, i) => {
                const bad = fileProblem(f);
                return (
                  <div key={i} className={`relative rounded-lg overflow-hidden ring-1 ${bad ? "ring-red-400" : "ring-slate-200"}`}>
                    <img src={URL.createObjectURL(f)} alt="" className="w-full h-20 object-cover bg-slate-100" />
                    <button
                      type="button"
                      onClick={() => setFiles(files.filter((_, j) => j !== i))}
                      className="absolute top-1 right-1 bg-black/60 hover:bg-black/80 text-white rounded-full w-5 h-5 text-xs leading-none"
                    >
                      &times;
                    </button>
                    {bad && (
                      <span className="absolute bottom-0 inset-x-0 bg-red-600/90 text-white text-[10px] text-center py-0.5">{bad}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full bg-sky-800 hover:bg-sky-700 text-white rounded-lg px-5 py-2.5 text-sm font-semibold transition disabled:opacity-60"
          >
            {busy ? "Uploading…" : "Upload"}
          </button>
        </form>
      </Card>
    </div>
  );
}
