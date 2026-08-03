import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Alert, Card, Field, inputCls } from "../components/ui";

export default function ChangePassword() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (pw1.length < 8) return setError("New password must be at least 8 characters.");
    if (pw1 !== pw2) return setError("Passwords do not match.");
    setBusy(true);
    try {
      const data = await api.post("/change-password", {
        current_password: current,
        new_password: pw1,
      });
      setUser(data.user);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto mt-8">
      <Card className="p-6">
        <h1 className="text-lg font-bold mb-4">Change password</h1>
        {user?.must_change_password && (
          <div className="mb-4 rounded bg-amber-100 border border-amber-200 text-amber-800 px-3 py-2 text-sm">
            You must change your password before continuing.
          </div>
        )}
        <Alert onClose={() => setError("")}>{error}</Alert>
        <form onSubmit={submit}>
          <Field label="Current password">
            <input className={inputCls} type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
          </Field>
          <Field label="New password" hint="At least 8 characters. Use something you don't use anywhere else.">
            <input className={inputCls} type="password" value={pw1} onChange={(e) => setPw1(e.target.value)} />
          </Field>
          <Field label="Confirm new password">
            <input className={inputCls} type="password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
          </Field>
          <button
            type="submit"
            disabled={busy}
            className="w-full bg-sky-800 hover:bg-sky-700 text-white rounded-lg px-5 py-2.5 text-sm font-semibold transition disabled:opacity-60"
          >
            {busy ? "Saving…" : "Change password"}
          </button>
        </form>
      </Card>
    </div>
  );
}
