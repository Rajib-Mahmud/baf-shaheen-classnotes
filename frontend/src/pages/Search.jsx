import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api";
import { NoteGrid, Spinner, inputCls } from "../components/ui";

export default function Search() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const [input, setInput] = useState(q);
  const [data, setData] = useState(null);

  useEffect(() => {
    setInput(q);
    if (q) {
      setData(null);
      api.get(`/search?q=${encodeURIComponent(q)}`).then(setData).catch(() => setData({ results: [] }));
    }
  }, [q]);

  return (
    <>
      <h1 className="text-xl font-bold mb-4">Search notes</h1>
      <form
        onSubmit={(e) => { e.preventDefault(); if (input.trim()) setParams({ q: input.trim() }); }}
        className="mb-6 flex gap-2"
      >
        <input className={`${inputCls} flex-1`} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Title, subject or chapter…" />
        <button className="bg-sky-800 hover:bg-sky-700 text-white rounded-lg px-4 py-2 text-sm">Search</button>
      </form>
      {q && !data && <Spinner />}
      {q && data && (
        <>
          <p className="text-sm text-slate-500 mb-4">
            {data.results.length} result{data.results.length !== 1 && "s"} for “{q}”
          </p>
          <NoteGrid notes={data.results} empty="Nothing found." />
        </>
      )}
    </>
  );
}
