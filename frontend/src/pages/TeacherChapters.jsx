import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Alert, Button, Card, Field, Spinner, inputCls } from "../components/ui";

export default function TeacherChapters() {
  const { id } = useParams();
  const [subject, setSubject] = useState(null);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [order, setOrder] = useState(0);
  const [editing, setEditing] = useState(null); // {id, title, order_index}

  const load = useCallback(() => {
    api.get(`/subject/${id}`).then(setSubject).catch((e) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  if (error && !subject) return <p className="text-red-600 text-sm">{error}</p>;
  if (!subject) return <Spinner />;

  const create = (e) => {
    e.preventDefault();
    api.post(`/teacher/subject/${id}/chapters`, { title, order_index: order })
      .then(() => { setTitle(""); setOrder(0); load(); })
      .catch((e2) => setError(e2.message));
  };
  const saveEdit = (e) => {
    e.preventDefault();
    api.put(`/teacher/chapter/${editing.id}`, { title: editing.title, order_index: editing.order_index })
      .then(() => { setEditing(null); load(); })
      .catch((e2) => setError(e2.message));
  };
  const remove = (chId) => {
    if (!confirm("Delete this chapter?")) return;
    api.del(`/teacher/chapter/${chId}`).then(load).catch((e2) => setError(e2.message));
  };

  return (
    <>
      <h1 className="text-xl font-bold mb-1">{subject.name} — chapters</h1>
      <p className="text-sm text-slate-500 mb-6">{subject.section_label}</p>
      <Alert onClose={() => setError("")}>{error}</Alert>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="p-5">
          <h2 className="font-semibold mb-4">Add chapter</h2>
          <form onSubmit={create}>
            <Field label="Chapter title">
              <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={160} />
            </Field>
            <Field label="Order">
              <input className={inputCls} type="number" min={0} value={order} onChange={(e) => setOrder(e.target.value)} />
            </Field>
            <Button type="submit">Save</Button>
          </form>
        </Card>

        <Card className="p-5">
          <h2 className="font-semibold mb-4">Chapters</h2>
          <ul className="divide-y divide-slate-100">
            {subject.chapters.length ? (
              subject.chapters.map((ch) =>
                editing?.id === ch.id ? (
                  <li key={ch.id} className="py-3">
                    <form onSubmit={saveEdit} className="flex gap-2 items-center flex-wrap">
                      <input
                        className={`${inputCls} flex-1 min-w-32`}
                        value={editing.title}
                        onChange={(e) => setEditing({ ...editing, title: e.target.value })}
                      />
                      <input
                        className={`${inputCls} w-20`}
                        type="number"
                        min={0}
                        value={editing.order_index}
                        onChange={(e) => setEditing({ ...editing, order_index: e.target.value })}
                      />
                      <Button type="submit" className="!px-3 !py-1.5">Save</Button>
                      <Button kind="ghost" type="button" className="!px-3 !py-1.5" onClick={() => setEditing(null)}>
                        Cancel
                      </Button>
                    </form>
                  </li>
                ) : (
                  <li key={ch.id} className="py-2 flex items-center justify-between gap-2">
                    <div>
                      <Link to={`/chapter/${ch.id}`} className="hover:underline text-sm">{ch.title}</Link>
                      <span className="text-xs text-slate-400"> · {ch.notes} note{ch.notes !== 1 && "s"} · order {ch.order_index}</span>
                    </div>
                    <div className="flex gap-2 items-center whitespace-nowrap text-xs">
                      <Link to={`/upload?chapter=${ch.id}`} className="text-emerald-700 hover:underline">Upload</Link>
                      <button onClick={() => setEditing({ ...ch })} className="text-sky-700 hover:underline">Edit</button>
                      <button onClick={() => remove(ch.id)} className="text-red-600 hover:underline">Delete</button>
                    </div>
                  </li>
                )
              )
            ) : (
              <li className="py-2 text-sm text-slate-400">No chapters yet.</li>
            )}
          </ul>
        </Card>
      </div>
    </>
  );
}
