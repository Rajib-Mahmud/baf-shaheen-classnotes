import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { Alert, Button, Field, inputCls } from "../components/ui";

const PANELS = {
  student: { title: "Student Login", hint: "Sign in with your roll-based ID.", btn: "bg-sky-800 hover:bg-sky-700" },
  teacher: { title: "Teacher Login", hint: "For subject teachers and class teachers.", btn: "bg-emerald-700 hover:bg-emerald-600" },
  admin: { title: "Admin Login", hint: "Authorised administrators only.", btn: "bg-slate-800 hover:bg-slate-700" },
};

export default function Login() {
  const [panel, setPanel] = useState("student");
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(panel, loginId, password);
      if (user.must_change_password) {
        navigate("/change-password");
      } else {
        const dest = location.state?.from?.pathname;
        navigate(dest && dest !== "/login" ? dest : "/", { replace: true });
      }
    } catch (err) {
      setError(err.message);
      if (err.data?.correct_panel) setPanel(err.data.correct_panel);
    } finally {
      setBusy(false);
    }
  };

  const p = PANELS[panel];
  return (
    <div className="max-w-sm mx-auto mt-6 sm:mt-12">
      <div className="text-center mb-5">
        <img src="/static/img/logo.png" alt="BAF Shaheen College Dhaka" className="h-20 w-auto mx-auto mb-3 drop-shadow-md" />
        <h1 className="text-xl font-bold">ClassNotes</h1>
        <p className="text-sm text-slate-500">BAF Shaheen College Dhaka</p>
        <p className="text-xs text-slate-400 mt-0.5">শিক্ষা · সংযম · শৃঙ্খলা</p>
      </div>

      <div className="grid grid-cols-3 gap-1 bg-slate-200/70 rounded-xl p-1 mb-4 text-sm font-medium">
        {Object.keys(PANELS).map((key) => (
          <button
            key={key}
            onClick={() => { setPanel(key); setError(""); }}
            className={`text-center rounded-lg py-2 transition capitalize ${
              key === panel ? "bg-white shadow text-slate-900" : "text-slate-500 hover:text-slate-800"
            }`}
          >
            {key}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl shadow-lg ring-1 ring-slate-200 p-7">
        <h2 className="font-bold text-lg mb-0.5">{p.title}</h2>
        <p className="text-xs text-slate-400 mb-5">{p.hint}</p>
        <Alert onClose={() => setError("")}>{error}</Alert>
        <form onSubmit={submit}>
          <Field label="Login ID">
            <input
              className={inputCls}
              value={loginId}
              onChange={(e) => setLoginId(e.target.value)}
              placeholder={panel === "student" ? "e.g. 9A-042" : ""}
              autoFocus
              autoComplete="username"
            />
          </Field>
          <Field label="Password">
            <div className="relative">
              <input
                className={`${inputCls} pr-10`}
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-medium"
              >
                {showPw ? "Hide" : "Show"}
              </button>
            </div>
          </Field>
          <button
            type="submit"
            disabled={busy}
            className={`w-full text-white rounded-lg px-5 py-2.5 text-sm font-semibold transition disabled:opacity-60 ${p.btn}`}
          >
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="text-xs text-slate-400 mt-5 text-center leading-relaxed">
          Accounts are issued by your teacher or the admin.
          <br />
          Forgot your password? Ask your class teacher to reset it.
        </p>
      </div>
    </div>
  );
}
