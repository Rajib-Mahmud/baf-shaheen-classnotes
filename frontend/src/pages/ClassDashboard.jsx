import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, Button, Card, Field, NoteGrid, Spinner, inputCls } from "../components/ui";

function StudentModal({ mode, student, onClose, onDone }) {
  const [loginId, setLoginId] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (mode === "create") {
        await api.post("/teacher/class/students", {
          login_id: loginId,
          full_name: fullName,
          password,
        });
      } else {
        await api.post(`/teacher/student/${student.id}/reset-password`, {
          new_password: password,
        });
      }
      onDone();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
        <div onClick={(e) => e.stopPropagation()}>
          <h2 className="font-bold mb-1">{mode === "create" ? "Add student" : `Reset password`}</h2>
          <p className="text-sm text-slate-500 mb-4">
            {mode === "create" ? "The account is created in your section." : `${student.full_name} (${student.login_id})`}
          </p>
          <Alert onClose={() => setError("")}>{error}</Alert>
          <form onSubmit={submit}>
            {mode === "create" && (
              <>
                <Field label="Login ID (roll-based)">
                  <input className={inputCls} value={loginId} onChange={(e) => setLoginId(e.target.value)} placeholder="e.g. 9A-042" />
                </Field>
                <Field label="Full name">
                  <input className={inputCls} value={fullName} onChange={(e) => setFullName(e.target.value)} />
                </Field>
              </>
            )}
            <Field
              label={mode === "create" ? "Initial password" : "New password"}
              hint="At least 8 characters. They must change it on first login."
            >
              <input className={inputCls} type="text" value={password} onChange={(e) => setPassword(e.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Button type="submit">{mode === "create" ? "Create student" : "Reset password"}</Button>
              <Button kind="ghost" type="button" onClick={onClose}>Cancel</Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  );
}

export default function ClassDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [modal, setModal] = useState(null); // {mode, student}

  const load = useCallback(() => {
    api.get("/teacher/class").then(setData).catch((e) => setError(e.message));
  }, []);
  useEffect(load, [load]);

  if (error && !data) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-xl font-bold">{data.section_label}</h1>
          <p className="text-sm text-slate-500">Class teacher view</p>
        </div>
        <div className="flex gap-2">
          <Link to="/leaderboard" className="bg-white ring-1 ring-slate-300 hover:bg-slate-50 rounded-lg px-3 py-1.5 text-sm">
            Leaderboard
          </Link>
          <Link
            to="/reports"
            className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
              data.open_reports ? "bg-red-600 hover:bg-red-500 text-white" : "bg-white ring-1 ring-slate-300 hover:bg-slate-50"
            }`}
          >
            Reports{data.open_reports ? ` (${data.open_reports})` : ""}
          </Link>
        </div>
      </div>

      <Alert kind="success" onClose={() => setFlash("")}>{flash}</Alert>
      <Alert onClose={() => setError("")}>{error}</Alert>

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Students ({data.students.length})</h2>
            <Button kind="success" className="!px-3 !py-1.5 !text-xs" onClick={() => setModal({ mode: "create" })}>
              + Add student
            </Button>
          </div>
          <ul className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            {data.students.length ? (
              data.students.map((s) => (
                <li key={s.id} className="py-2 flex items-center justify-between text-sm gap-2">
                  <span className="min-w-0 truncate">
                    {s.full_name} <span className="font-mono text-xs text-slate-400">{s.login_id}</span>
                  </span>
                  <button
                    onClick={() => setModal({ mode: "reset", student: s })}
                    className="text-sky-700 text-xs hover:underline whitespace-nowrap"
                  >
                    Reset password
                  </button>
                </li>
              ))
            ) : (
              <li className="py-2 text-sm text-slate-400">No students yet.</li>
            )}
          </ul>
        </Card>

        <div className="lg:col-span-2">
          <Card className="p-5 mb-6">
            <h2 className="font-semibold mb-3">Subjects</h2>
            <div className="flex flex-wrap gap-2">
              {data.subjects.length ? (
                data.subjects.map((s) => (
                  <Link key={s.id} to={`/subject/${s.id}`} className="bg-slate-100 hover:bg-slate-200 rounded px-3 py-1.5 text-sm">
                    {s.name}
                  </Link>
                ))
              ) : (
                <span className="text-sm text-slate-400">No subjects yet.</span>
              )}
            </div>
          </Card>

          <h2 className="font-semibold mb-3">Recent notes</h2>
          <NoteGrid notes={data.recent_notes} empty="No notes yet." />
        </div>
      </div>

      {modal && (
        <StudentModal
          mode={modal.mode}
          student={modal.student}
          onClose={() => setModal(null)}
          onDone={() => {
            setFlash(modal.mode === "create" ? "Student created. They must change the password on first login." : "Password reset. They must change it on next login.");
            setModal(null);
            load();
          }}
        />
      )}
    </>
  );
}
