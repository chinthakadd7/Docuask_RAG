// Every call to the FastAPI backend lives here, so the rest of the app never touches fetch().

export class ApiError extends Error {
  constructor(status, type, message) {
    super(message);
    this.status = status; // HTTP status, or 0 when the server could not be reached
    this.type = type; // our error name, e.g. "NoExtractableTextError"
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, options);
  } catch (err) {
    if (err.name === 'AbortError') throw err; // the user pressed Stop
    throw new ApiError(0, 'NetworkError', 'Can’t reach the DocuAsk server. Is it running?');
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // the response had no JSON body
  }

  if (!response.ok) {
    // Our backend always answers errors as {"error": {"type": ..., "message": ...}}
    const error = data?.error;
    throw new ApiError(
      response.status,
      error?.type ?? 'HttpError',
      error?.message ?? `The request failed (${response.status}).`,
    );
  }
  return data;
}

export const getConfig = () => request('/config');
export const listDocuments = () => request('/documents');
export const deleteDocument = (id) =>
  request(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });

export function uploadDocument(file) {
  const body = new FormData();
  body.append('file', file);
  return request('/documents', { method: 'POST', body });
}

export function askQuestion(question, docIds, signal) {
  return request('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, doc_ids: docIds }), // undefined is left out = search everything
    signal,
  });
}
