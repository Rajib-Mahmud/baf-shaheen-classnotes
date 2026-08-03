import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, Button, Card, Field, Spinner, inputCls } from "../components/ui";

const ROLE_LABELS = {
  student: "Student",
  class_teacher: "Class Teacher",
  subject_teacher: "Subject Teacher",
  super_admin: "Super Admin",
};

function Overview({ data }) {
  const s = data.stats;
  const items = [
    ["Classes", s.classes], ["Sections", s.sections], ["Subjects", s.subjects],
    ["Students", s.students], ["Teachers", s.teachers], ["Notes", s.notes],
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
      {items.map(([label, value]) => (
        <Card key={label} className="p-4">
          <div className="text-2xl font-bold">{value}</div>
          <div className="text-sm text-slate-500">{label}</div>
        </Card>
      ))}
      <Link
        to="/reports"
        className={`rounded-xl shadow-sm p-4 block transition ring-1 ring-slate-200 ${
          s.open_reports ? "bg-red-600 text-white hover:bg-red-500" : "bg-white hover:bg-slate-50"
        }`}
      >
        <div className="text-2xl font-bold">{s.open_reports}</div>
        <div className={`text-sm ${s.open_reports ? "text-red-100" : "text-slate-500"}`}>Open reports</div>
      </Link>
    </div>
  );
}

function Structure({ data, reload, setError, setFlash }) {
  const [className, setClassName] = useState("");
  const [sectionName, setSectionName] = useState("");
  const [sectionClass, setSectionClass] = useState("");
  const [subjectName, setSubjectName] = useState("");
  const [subjectSection, setSubjectSection] = useState("");
  const [subjectTeacher, setSubjectTeacher] = useState("");

  const run = (promise, msg) =>
    promise.then(() => { setFlash(msg); reload(); }).catch((e) => setError(e.message));

  return (
    <div className="grid md:grid-cols-3 gap-6">
      <Card className="p-5">
        <h2 className="font-semibold mb-3">Classes</h2>
        <form
          onSubmit={(e) => { e.preventDefault(); run(api.post("/admin/classes", { name: className }), "Class created."); setClassName(""); }}
          className="flex gap-2 mb-3"
        >
          <input className={`${inputCls} flex-1`} value={className} onChange={(e) => setClassName(e.target.value)} placeholder="e.g. Class 9" />
          <Button type="submit" className="!px-3">Add</Button>
        </form>
        <ul className="divide-y divide-slate-100 text-sm">
          {data.classes.map((c) => (
            <li key={c.id} className="py-2 flex justify-between items-center">
              <span>{c.name} <span className="text-xs text-slate-400">({c.sections} section{c.sections !== 1 && "s"})</span></span>
              <button
                onClick={() => confirm(`Delete ${c.name}?`) && run(api.del(`/admin/classes/${c.id}`), "Class deleted.")}
                className="text-red-600 text-xs hover:underline"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-5">
        <h2 className="font-semibold mb-3">Sections</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(api.post("/admin/sections", { name: sectionName, class_id: Number(sectionClass) }), "Section created.");
            setSectionName("");
          }}
          className="space-y-2 mb-3"
        >
          <select className={inputCls} value={sectionClass} onChange={(e) => setSectionClass(e.target.value)}>
            <option value="">— Class —</option>
            {data.classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <div className="flex gap-2">
            <input className={`${inputCls} flex-1`} value={sectionName} onChange={(e) => setSectionName(e.target.value)} placeholder="e.g. A" />
            <Button type="submit" className="!px-3">Add</Button>
          </div>
        </form>
        <ul className="divide-y divide-slate-100 text-sm">
          {data.sections.map((s) => (
            <li key={s.id} className="py-2 flex justify-between items-center">
              <span>{s.label}</span>
              <button
                onClick={() => confirm(`Delete ${s.label}?`) && run(api.del(`/admin/sections/${s.id}`), "Section deleted.")}
                className="text-red-600 text-xs hover:underline"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-5">
        <h2 className="font-semibold mb-3">Subjects</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run(
              api.post("/admin/subjects", {
                name: subjectName,
                section_id: Number(subjectSection),
                teacher_id: subjectTeacher ? Number(subjectTeacher) : null,
              }),
              "Subject created."
            );
            setSubjectName("");
          }}
          className="space-y-2 mb-3"
        >
          <select className={inputCls} value={subjectSection} onChange={(e) => setSubjectSection(e.target.value)}>
            <option value="">— Class & section —</option>
            {data.sections.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <select className={inputCls} value={subjectTeacher} onChange={(e) => setSubjectTeacher(e.target.value)}>
            <option value="">— Teacher (optional) —</option>
            {data.teachers.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
          </select>
          <div className="flex gap-2">
            <input className={`${inputCls} flex-1`} value={subjectName} onChange={(e) => setSubjectName(e.target.value)} placeholder="e.g. Physics" />
            <Button type="submit" className="!px-3">Add</Button>
          </div>
        </form>
        <ul className="divide-y divide-slate-100 text-sm">
          {data.subjects.map((s) => (
            <li key={s.id} className="py-2">
              <div className="flex justify-between items-center">
                <span className="font-medium">{s.name} <span className="text-xs text-slate-400 font-normal">· {s.section_label}</span></span>
                <button
                  onClick={() => confirm(`Delete ${s.name}?`) && run(api.del(`/admin/subjects/${s.id}`), "Subject deleted.")}
                  className="text-red-600 text-xs hover:underline"
                >
                  Delete
                </button>
              </div>
              <div className="flex gap-2 items-center mt-1">
                <select
                  className="rounded border border-slate-300 px-2 py-1 text-xs bg-white flex-1"
                  value={s.teacher_id || ""}
                  onChange={(e) =>
                    run(api.put(`/admin/subjects/${s.id}`, { teacher_id: e.target.value ? Number(e.target.value) : null }), "Teacher assignment updated.")
                  }
                >
                  <option value="">— Unassigned —</option>
                  {data.teachers.map((t) => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                </select>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function Users({ data, reload, setError, setFlash }) {
  const [users, setUsers] = useState(null);
  const [roleFilter, setRoleFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ role: "student", login_id: "", full_name: "", section_id: "", password: "" });
  const [resetFor, setResetFor] = useState(null);
  const [resetPw, setResetPw] = useState("");

  const loadUsers = useCallback(() => {
    api.get(`/admin/users${roleFilter ? `?role=${roleFilter}` : ""}`).then((d) => setUsers(d.users)).catch((e) => setError(e.message));
  }, [roleFilter, setError]);
  useEffect(loadUsers, [loadUsers]);

  const run = (promise, msg) =>
    promise.then(() => { setFlash(msg); loadUsers(); reload(); }).catch((e) => setError(e.message));

  const createUser = (e) => {
    e.preventDefault();
    run(
      api.post("/admin/users", { ...form, section_id: form.section_id ? Number(form.section_id) : null }),
      "User created. They must change the password on first login."
    );
    setShowCreate(false);
    setForm({ role: "student", login_id: "", full_name: "", section_id: "", password: "" });
  };

  return (
    <>
      <div className="flex flex-wrap gap-2 mb-4 text-sm items-center">
        {["", "student", "subject_teacher", "class_teacher", "super_admin"].map((r) => (
          <button
            key={r}
            onClick={() => setRoleFilter(r)}
            className={`px-3 py-1 rounded ${roleFilter === r ? "bg-sky-800 text-white" : "bg-white ring-1 ring-slate-200"}`}
          >
            {r ? ROLE_LABELS[r] + "s" : "All"}
          </button>
        ))}
        <Button kind="success" className="ml-auto !px-3 !py-1.5 !text-xs" onClick={() => setShowCreate(!showCreate)}>
          + New user
        </Button>
      </div>

      {showCreate && (
        <Card className="p-5 mb-4 max-w-md">
          <h2 className="font-semibold mb-3">Create user</h2>
          <form onSubmit={createUser}>
            <Field label="Role">
              <select className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="student">Student</option>
                <option value="class_teacher">Class Teacher</option>
                <option value="subject_teacher">Subject Teacher</option>
              </select>
            </Field>
            <Field label="Login ID" hint="For students, use the roll-based ID (e.g. 9A-042).">
              <input className={inputCls} value={form.login_id} onChange={(e) => setForm({ ...form, login_id: e.target.value })} />
            </Field>
            <Field label="Full name">
              <input className={inputCls} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </Field>
            <Field label="Class & section" hint="Required for students and class teachers.">
              <select className={inputCls} value={form.section_id} onChange={(e) => setForm({ ...form, section_id: e.target.value })}>
                <option value="">— None —</option>
                {data.sections.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </Field>
            <Field label="Initial password" hint="At least 8 characters; must be changed on first login.">
              <input className={inputCls} type="text" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </Field>
            <Button type="submit">Create user</Button>
          </form>
        </Card>
      )}

      {resetFor && (
        <Card className="p-5 mb-4 max-w-md">
          <h2 className="font-semibold mb-1">Reset password</h2>
          <p className="text-sm text-slate-500 mb-3">{resetFor.full_name} ({resetFor.login_id})</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              run(api.post(`/admin/users/${resetFor.id}/reset-password`, { new_password: resetPw }), "Password reset.");
              setResetFor(null);
              setResetPw("");
            }}
            className="flex gap-2"
          >
            <input className={`${inputCls} flex-1`} type="text" value={resetPw} onChange={(e) => setResetPw(e.target.value)} placeholder="New password (8+ chars)" />
            <Button type="submit" className="!px-3">Reset</Button>
            <Button kind="ghost" type="button" className="!px-3" onClick={() => setResetFor(null)}>Cancel</Button>
          </form>
        </Card>
      )}

      {!users ? (
        <Spinner />
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2">Login ID</th>
                <th className="px-4 py-2">Name</th>
                <th className="px-4 py-2">Role</th>
                <th className="px-4 py-2">Class · Section</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {users.map((u) => (
                <tr key={u.id} className={u.is_active ? "" : "opacity-50"}>
                  <td className="px-4 py-2 font-mono text-xs">{u.login_id}</td>
                  <td className="px-4 py-2">{u.full_name}</td>
                  <td className="px-4 py-2">{u.role_label}</td>
                  <td className="px-4 py-2">{u.section_label || "—"}</td>
                  <td className="px-4 py-2">
                    {u.is_active ? <span className="text-green-700 text-xs">Active</span> : <span className="text-red-600 text-xs">Deactivated</span>}
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap text-xs">
                    <button onClick={() => setResetFor(u)} className="text-sky-700 hover:underline mr-2">Reset password</button>
                    {u.role !== "super_admin" && (
                      <button
                        onClick={() => run(api.post(`/admin/users/${u.id}/toggle-active`), u.is_active ? "User deactivated." : "User activated.")}
                        className={u.is_active ? "text-red-600 hover:underline" : "text-green-700 hover:underline"}
                      >
                        {u.is_active ? "Deactivate" : "Activate"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}

function ImportStudents({ data, setError }) {
  const [sectionId, setSectionId] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!sectionId || !file) return setError("Pick a section and a CSV file.");
    setBusy(true);
    const fd = new FormData();
    fd.append("section_id", sectionId);
    fd.append("csv_file", file);
    try {
      setResult(await api.postForm("/admin/import-students", fd));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <Card className="p-5 mb-4">
        <h2 className="font-semibold mb-2">Bulk import students (CSV)</h2>
        <p className="text-sm text-slate-500 mb-4">
          Columns: <code className="bg-slate-100 px-1 rounded">login_id, full_name, password</code>. Password column is
          optional — generated passwords are shown once below.
        </p>
        <form onSubmit={submit} className="space-y-3">
          <select className={inputCls} value={sectionId} onChange={(e) => setSectionId(e.target.value)}>
            <option value="">— Class & section —</option>
            {data.sections.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} className="text-sm" />
          <div>
            <Button type="submit" disabled={busy}>{busy ? "Importing…" : "Import students"}</Button>
          </div>
        </form>
      </Card>

      {result && (
        <>
          <p className="text-sm text-red-600 mb-3 font-medium">Save this now: generated passwords are shown only once.</p>
          {result.created.length > 0 && (
            <Card className="overflow-x-auto mb-4">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-slate-500">
                  <tr><th className="px-4 py-2">Login ID</th><th className="px-4 py-2">Name</th><th className="px-4 py-2">Initial password</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.created.map((r) => (
                    <tr key={r.login_id}>
                      <td className="px-4 py-2 font-mono text-xs">{r.login_id}</td>
                      <td className="px-4 py-2">{r.full_name}</td>
                      <td className="px-4 py-2 font-mono text-xs">{r.password}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
          {result.errors.length > 0 && (
            <Card className="p-4 bg-red-50 border-red-200">
              <h3 className="font-semibold text-red-800 text-sm mb-2">Skipped rows</h3>
              <ul className="text-sm text-red-700 list-disc list-inside">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default function Admin() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");

  const reload = useCallback(() => {
    api.get("/admin/overview").then(setData).catch((e) => setError(e.message));
  }, []);
  useEffect(reload, [reload]);

  if (error && !data) return <p className="text-red-600 text-sm">{error}</p>;
  if (!data) return <Spinner />;

  const tabs = [
    ["overview", "Overview"],
    ["structure", "Classes & subjects"],
    ["users", "Users"],
    ["import", "Import CSV"],
  ];

  return (
    <>
      <h1 className="text-xl font-bold mb-4">Admin</h1>
      <div className="flex flex-wrap gap-2 mb-6 text-sm">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            onClick={() => { setTab(key); setFlash(""); setError(""); }}
            className={`px-4 py-2 rounded-lg ${tab === key ? "bg-sky-800 text-white" : "bg-white ring-1 ring-slate-200 hover:bg-slate-50"}`}
          >
            {label}
          </button>
        ))}
      </div>

      <Alert kind="success" onClose={() => setFlash("")}>{flash}</Alert>
      <Alert onClose={() => setError("")}>{error}</Alert>

      {tab === "overview" && <Overview data={data} />}
      {tab === "structure" && <Structure data={data} reload={reload} setError={setError} setFlash={setFlash} />}
      {tab === "users" && <Users data={data} reload={reload} setError={setError} setFlash={setFlash} />}
      {tab === "import" && <ImportStudents data={data} setError={setError} />}
    </>
  );
}
