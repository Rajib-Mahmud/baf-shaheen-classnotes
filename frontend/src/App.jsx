import { useState } from "react";
import { Link, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./AuthContext";
import { Spinner } from "./components/ui";
import Login from "./pages/Login";
import ChangePassword from "./pages/ChangePassword";
import Dashboard from "./pages/Dashboard";
import Subject from "./pages/Subject";
import Chapter from "./pages/Chapter";
import Note from "./pages/Note";
import Upload from "./pages/Upload";
import Search from "./pages/Search";
import Leaderboard from "./pages/Leaderboard";
import TeacherSubjects from "./pages/TeacherSubjects";
import TeacherChapters from "./pages/TeacherChapters";
import ClassDashboard from "./pages/ClassDashboard";
import Reports from "./pages/Reports";
import Admin from "./pages/Admin";

function homeFor(user) {
  if (!user) return "/login";
  if (user.role === "super_admin") return "/admin";
  if (user.role === "subject_teacher") return "/teacher";
  if (user.role === "class_teacher") return "/class";
  return "/";
}

function Nav() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  if (!user) return null;

  const links = {
    super_admin: [
      ["/admin", "Admin"],
      ["/reports", "Reports"],
    ],
    subject_teacher: [
      ["/teacher", "My subjects"],
      ["/upload", "+ Upload"],
    ],
    class_teacher: [
      ["/class", "My class"],
      ["/leaderboard", "Leaderboard"],
      ["/reports", "Reports"],
    ],
    student: [
      ["/", "Home"],
      ["/leaderboard", "Leaderboard"],
      ["/upload", "+ Upload"],
    ],
  }[user.role];

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };
  const doSearch = (e) => {
    e.preventDefault();
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q.trim())}`);
    setOpen(false);
  };

  return (
    <nav className="bg-sky-900 text-white shadow sticky top-0 z-40">
      <div className="max-w-5xl mx-auto px-4">
        <div className="flex items-center justify-between h-14 gap-3">
          <Link to={homeFor(user)} className="flex items-center gap-2.5 min-w-0">
            <img src="/static/img/logo.png" alt="BAF Shaheen College Dhaka" className="h-9 w-auto drop-shadow" />
            <span className="truncate leading-tight">
              <span className="font-bold tracking-tight block">ClassNotes</span>
              <span className="hidden sm:block text-sky-300 text-[11px] font-medium -mt-0.5">
                BAF Shaheen College Dhaka
              </span>
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1 text-sm">
            {links.map(([to, label]) => (
              <Link
                key={to}
                to={to}
                className={`px-3 py-1.5 rounded-md ${
                  label.startsWith("+") ? "bg-emerald-600 hover:bg-emerald-500 font-medium ml-1" : "hover:bg-sky-800"
                }`}
              >
                {label}
              </Link>
            ))}
            {user.role !== "super_admin" && (
              <form onSubmit={doSearch} className="ml-2">
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search notes…"
                  className="rounded-md px-3 py-1.5 text-slate-800 text-sm w-44 focus:w-56 transition-all bg-white placeholder-slate-400 outline-none"
                />
              </form>
            )}
            <span className="text-sky-300 text-xs ml-2 max-w-32 truncate">{user.full_name}</span>
            <Link to="/change-password" className="px-2 py-1.5 rounded-md hover:bg-sky-800 text-xs">
              Password
            </Link>
            <button onClick={doLogout} className="bg-sky-700 hover:bg-sky-600 rounded-md px-3 py-1.5 text-xs ml-1">
              Logout
            </button>
          </div>

          <button className="md:hidden p-2 rounded-md hover:bg-sky-800" onClick={() => setOpen(!open)} aria-label="Menu">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {open && (
          <div className="md:hidden pb-3 border-t border-sky-800 pt-2 text-sm">
            {user.role !== "super_admin" && (
              <form onSubmit={doSearch} className="mb-2">
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search notes…"
                  className="w-full rounded-md px-3 py-2 text-slate-800 bg-white placeholder-slate-400 outline-none"
                />
              </form>
            )}
            {links.map(([to, label]) => (
              <Link
                key={to}
                to={to}
                onClick={() => setOpen(false)}
                className={`block px-3 py-2 rounded-md ${
                  label.startsWith("+") ? "bg-emerald-600 font-medium" : "hover:bg-sky-800"
                }`}
              >
                {label}
              </Link>
            ))}
            <div className="border-t border-sky-800 mt-2 pt-2">
              <div className="px-3 py-1 text-sky-300 text-xs">
                {user.full_name} · {user.role_label}
              </div>
              <Link to="/change-password" onClick={() => setOpen(false)} className="block px-3 py-2 rounded-md hover:bg-sky-800">
                Change password
              </Link>
              <button onClick={doLogout} className="block w-full text-left px-3 py-2 rounded-md hover:bg-sky-800 text-red-300">
                Logout
              </button>
            </div>
          </div>
        )}
      </div>
    </nav>
  );
}

function Protected({ children, roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (user.must_change_password && location.pathname !== "/change-password")
    return <Navigate to="/change-password" replace />;
  if (roles && !roles.includes(user.role) && user.role !== "super_admin")
    return <Navigate to={homeFor(user)} replace />;
  return children;
}

function Shell() {
  const { user, loading } = useAuth();
  return (
    <div className="min-h-screen flex flex-col">
      <Nav />
      <main className="max-w-5xl mx-auto px-4 py-6 w-full flex-1">
        {loading ? (
          <Spinner />
        ) : (
          <Routes>
            <Route path="/login" element={user && !user.must_change_password ? <Navigate to={homeFor(user)} /> : <Login />} />
            <Route path="/change-password" element={<Protected><ChangePassword /></Protected>} />
            <Route path="/" element={<Protected roles={["student"]}><Dashboard /></Protected>} />
            <Route path="/subject/:id" element={<Protected><Subject /></Protected>} />
            <Route path="/chapter/:id" element={<Protected><Chapter /></Protected>} />
            <Route path="/note/:id" element={<Protected><Note /></Protected>} />
            <Route path="/upload" element={<Protected roles={["student", "subject_teacher"]}><Upload /></Protected>} />
            <Route path="/search" element={<Protected><Search /></Protected>} />
            <Route path="/leaderboard" element={<Protected roles={["student", "class_teacher"]}><Leaderboard /></Protected>} />
            <Route path="/teacher" element={<Protected roles={["subject_teacher"]}><TeacherSubjects /></Protected>} />
            <Route path="/teacher/subject/:id" element={<Protected roles={["subject_teacher"]}><TeacherChapters /></Protected>} />
            <Route path="/class" element={<Protected roles={["class_teacher"]}><ClassDashboard /></Protected>} />
            <Route path="/reports" element={<Protected roles={["class_teacher"]}><Reports /></Protected>} />
            <Route path="/admin" element={<Protected roles={[]}><Admin /></Protected>} />
            <Route path="*" element={<Navigate to={homeFor(user)} />} />
          </Routes>
        )}
      </main>
      <footer className="max-w-5xl mx-auto px-4 py-6 text-center text-xs text-slate-400 w-full">
        ClassNotes — BAF Shaheen College Dhaka · EIIN-107858 · শিক্ষা সংযম শৃঙ্খলা
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}
