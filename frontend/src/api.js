// Minimal same-origin API client. Session cookie carries auth; every
// mutating call sends the CSRF token in the X-CSRFToken header.

let csrfToken = null;

export function setCsrf(token) {
  csrfToken = token;
}

async function request(path, { method = "GET", body, formData } = {}) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (formData) {
    opts.body = formData;
  } else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (method !== "GET" && csrfToken) {
    opts.headers["X-CSRFToken"] = csrfToken;
  }
  const res = await fetch(`/api${path}`, opts);
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const error = new Error(data?.error || `Request failed (${res.status})`);
    error.status = res.status;
    error.data = data;
    throw error;
  }
  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  del: (path) => request(path, { method: "DELETE" }),
  postForm: (path, formData) => request(path, { method: "POST", formData }),
};
