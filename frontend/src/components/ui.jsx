import { Link } from "react-router-dom";

export function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="w-8 h-8 border-4 border-sky-200 border-t-sky-700 rounded-full animate-spin" />
    </div>
  );
}

export function Card({ children, className = "" }) {
  return (
    <div className={`bg-white rounded-xl shadow-sm ring-1 ring-slate-200 ${className}`}>
      {children}
    </div>
  );
}

export function Alert({ kind = "error", children, onClose }) {
  if (!children) return null;
  const styles =
    kind === "error"
      ? "bg-red-50 text-red-800 border-red-200"
      : "bg-emerald-50 text-emerald-800 border-emerald-200";
  return (
    <div className={`mb-4 rounded-lg px-4 py-3 text-sm border flex justify-between gap-3 ${styles}`}>
      <span>{children}</span>
      {onClose && (
        <button onClick={onClose} className="opacity-50 hover:opacity-100 font-bold">
          &times;
        </button>
      )}
    </div>
  );
}

export function Field({ label, hint, error, children }) {
  return (
    <div className="mb-4">
      {label && <label className="block text-sm font-medium mb-1 text-slate-700">{label}</label>}
      {children}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
      {error && <p className="text-red-600 text-xs mt-1">{error}</p>}
    </div>
  );
}

export const inputCls =
  "w-full rounded-lg border-slate-300 border px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-sky-500 focus:border-sky-500 outline-none";

export function Button({ children, kind = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-sky-800 hover:bg-sky-700 text-white",
    success: "bg-emerald-600 hover:bg-emerald-500 text-white",
    danger: "bg-red-600 hover:bg-red-500 text-white",
    warn: "bg-amber-500 hover:bg-amber-400 text-white",
    ghost: "bg-white ring-1 ring-slate-300 hover:bg-slate-50 text-slate-700",
  }[kind];
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-60 disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({ kind, children }) {
  const styles = {
    official: "bg-amber-400/95 text-amber-950",
    student: "bg-white/90 text-slate-600 ring-1 ring-slate-200",
    hidden: "bg-slate-800 text-white",
    plain: "bg-slate-100 text-slate-600",
  }[kind || "plain"];
  return (
    <span className={`text-[10px] uppercase font-bold rounded-md px-1.5 py-0.5 shadow-sm ${styles}`}>
      {children}
    </span>
  );
}

export function NoteCard({ note }) {
  return (
    <Link
      to={`/note/${note.id}`}
      className="group block bg-white rounded-xl shadow-sm hover:shadow-md ring-1 ring-slate-200 hover:ring-sky-300 transition overflow-hidden"
    >
      <div className="relative">
        {note.thumb_image_id ? (
          <img
            src={`/image/${note.thumb_image_id}?thumb=1`}
            alt={note.title}
            loading="lazy"
            className="w-full h-36 object-cover bg-slate-200 group-hover:scale-[1.02] transition-transform"
          />
        ) : (
          <div className="w-full h-36 bg-slate-200 grid place-items-center text-slate-400 text-xs">
            No photo
          </div>
        )}
        <div className="absolute top-2 left-2 flex gap-1">
          {note.is_official ? <Badge kind="official">★ Official</Badge> : <Badge kind="student">Student note</Badge>}
          {note.is_hidden && <Badge kind="hidden">Hidden</Badge>}
        </div>
        <div className="absolute bottom-2 right-2 flex gap-1">
          {note.votes > 0 && (
            <span className="text-[10px] font-semibold bg-black/60 text-white rounded-md px-1.5 py-0.5">
              ▲ {note.votes}
            </span>
          )}
          {note.pages > 1 && (
            <span className="text-[10px] font-semibold bg-black/60 text-white rounded-md px-1.5 py-0.5">
              {note.pages} pages
            </span>
          )}
        </div>
      </div>
      <div className="p-3">
        <h3 className="font-medium text-sm leading-snug line-clamp-2">{note.title}</h3>
        <p className="text-xs text-slate-500 mt-1 truncate">
          {note.uploader} · {note.created_at}
        </p>
      </div>
    </Link>
  );
}

export function NoteGrid({ notes, empty }) {
  if (!notes.length)
    return (
      <Card className="p-8 text-center col-span-full">
        <p className="text-sm text-slate-500">{empty || "No notes yet."}</p>
      </Card>
    );
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
      {notes.map((n) => (
        <NoteCard key={n.id} note={n} />
      ))}
    </div>
  );
}

export function Breadcrumb({ items }) {
  return (
    <nav className="text-sm text-slate-500 mb-3 flex flex-wrap items-center gap-1">
      {items.map(([label, href], i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span className="text-slate-300">/</span>}
          {href ? (
            <Link to={href} className="hover:text-sky-700 hover:underline">
              {label}
            </Link>
          ) : (
            <span className="text-slate-700 font-medium">{label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
