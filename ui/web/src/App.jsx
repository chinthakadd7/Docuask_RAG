import { useEffect, useRef, useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Chat from './components/Chat.jsx';
import SourcePanel from './components/SourcePanel.jsx';
import { askQuestion, deleteDocument, getConfig, listDocuments, uploadDocument } from './api.js';
import { claimFor } from './text.js';

let counter = 0;
const uid = () => `id${++counter}`;
const toDoc = (d) => ({ id: d.doc_id, name: d.file_name, chunks: d.chunks, status: 'ready' });
const isWide = () => window.matchMedia('(min-width: 1101px)').matches;

function uploadMessage(name, err) {
  switch (err.type) {
    case 'NoExtractableTextError':
      return `${name} looks like a scanned PDF. OCR isn’t supported yet.`;
    case 'EncryptedPDFError':
      return `${name} is password protected, so it can’t be read.`;
    case 'InvalidPDFError':
      return `${name} isn’t a PDF. Please choose a PDF file.`;
    case 'FileTooLargeError':
      return `${name} is larger than the upload limit.`;
    default:
      return `${name}: ${err.message}`;
  }
}

export default function App() {
  const [maxMb, setMaxMb] = useState(20);
  const [docs, setDocs] = useState([]); // {id, name, chunks, status: 'ready' | 'reading'}
  const [notices, setNotices] = useState([]); // {id, tone: 'error' | 'info', text}
  const [messages, setMessages] = useState([]);
  const [selected, setSelected] = useState(null); // {messageId, number}
  const [scope, setScope] = useState('all'); // 'all' or one doc id
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const abortRef = useRef(null);
  const fileInputRef = useRef(null);
  const composerRef = useRef(null);

  const readyDocs = docs.filter((d) => d.status === 'ready');

  const addNotice = (tone, text) =>
    setNotices((list) => [...list, { id: uid(), tone, text }].slice(-4));
  const dismissNotice = (id) => setNotices((list) => list.filter((n) => n.id !== id));
  const patch = (id, changes) =>
    setMessages((list) => list.map((m) => (m.id === id ? { ...m, ...changes } : m)));

  // ---- Load settings and the documents already on the server ----
  async function refreshDocs() {
    const list = await listDocuments();
    setDocs((current) => [...list.map(toDoc), ...current.filter((d) => d.status === 'reading')]);
  }

  useEffect(() => {
    getConfig().then((c) => setMaxMb(c.max_file_mb)).catch(() => {});
    refreshDocs().catch((err) => addNotice('error', err.message));
  }, []);

  // ---- Documents ----
  function pickFile() {
    fileInputRef.current?.click();
  }

  async function uploadFiles(files) {
    setDrawer(false);
    for (const file of files) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        addNotice('error', `${file.name} isn’t a PDF. Please choose a PDF file.`);
        continue;
      }
      if (file.size > maxMb * 1024 * 1024) {
        addNotice('error', `${file.name} is larger than ${maxMb} MB.`);
        continue;
      }
      const tempId = uid();
      setDocs((list) => [...list, { id: tempId, name: file.name, status: 'reading' }]);
      try {
        const result = await uploadDocument(file);
        setDocs((list) => list.filter((d) => d.id !== tempId));
        if (result.status === 'duplicate') {
          addNotice('info', `${file.name} is already uploaded. Nothing was re-processed.`);
          await refreshDocs();
        } else {
          setDocs((list) => [
            ...list,
            { id: result.doc_id, name: result.file_name, chunks: result.chunk_count, status: 'ready' },
          ]);
        }
      } catch (err) {
        setDocs((list) => list.filter((d) => d.id !== tempId));
        addNotice('error', uploadMessage(file.name, err));
      }
    }
  }

  async function removeDoc(doc) {
    if (!window.confirm(`Delete ${doc.name}? Its passages will be removed.`)) return;
    try {
      await deleteDocument(doc.id);
      setDocs((list) => list.filter((d) => d.id !== doc.id));
      if (scope === doc.id) setScope('all');
    } catch (err) {
      addNotice('error', err.message);
    }
  }

  // ---- Questions ----
  async function runAsk(botId, question, docScope) {
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    try {
      const answer = await askQuestion(
        question,
        docScope === 'all' ? undefined : [docScope],
        controller.signal,
      );
      patch(botId, { status: 'done', answer });
      // On wide screens, show the first source straight away (as in the design).
      if (answer.sources.length > 0 && isWide()) {
        setSelected({ messageId: botId, number: answer.sources[0].number });
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        patch(botId, { status: 'stopped' });
      } else {
        patch(botId, {
          status: 'error',
          error: { type: err.type, status: err.status, message: err.message },
        });
      }
      setDraft((current) => current || question); // put the question back in the box
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function send(text) {
    const question = (text ?? draft).trim();
    if (!question || busy || readyDocs.length === 0) return;
    const searched =
      scope === 'all'
        ? readyDocs.map((d) => d.name)
        : readyDocs.filter((d) => d.id === scope).map((d) => d.name);
    const botId = uid();
    setMessages((list) => [
      ...list,
      { id: uid(), role: 'user', text: question },
      { id: botId, role: 'assistant', status: 'loading', question, scope, searched },
    ]);
    setDraft('');
    setSelected(null);
    runAsk(botId, question, scope);
  }

  function retry(botId) {
    const message = messages.find((m) => m.id === botId);
    if (!message || busy) return;
    patch(botId, { status: 'loading', error: null });
    setDraft('');
    runAsk(botId, message.question, message.scope);
  }

  function rephrase(question) {
    setDraft(question);
    composerRef.current?.focus();
  }

  // ---- What the source panel shows ----
  const selectedMessage = messages.find((m) => m.id === selected?.messageId);
  const source = selectedMessage?.answer?.sources.find((s) => s.number === selected.number) ?? null;
  const claim = source ? claimFor(selectedMessage.answer.answer, source.number) : '';
  const hasDocs = docs.length > 0;

  return (
    <div className={`app${hasDocs ? '' : ' no-docs'}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(e) => {
          uploadFiles(Array.from(e.target.files));
          e.target.value = ''; // lets the same file be chosen again
        }}
      />

      <Sidebar
        docs={docs}
        notices={notices}
        maxMb={maxMb}
        open={drawer}
        onPick={pickFile}
        onFiles={uploadFiles}
        onDelete={removeDoc}
        onDismiss={dismissNotice}
        onClose={() => setDrawer(false)}
      />
      {drawer && <div className="backdrop" onClick={() => setDrawer(false)} />}

      <Chat
        docs={docs}
        readyDocs={readyDocs}
        messages={messages}
        selected={selected}
        scope={scope}
        setScope={setScope}
        draft={draft}
        setDraft={setDraft}
        busy={busy}
        composerRef={composerRef}
        maxMb={maxMb}
        onSend={send}
        onStop={() => abortRef.current?.abort()}
        onRetry={retry}
        onRephrase={rephrase}
        onChip={(messageId, number) => setSelected({ messageId, number })}
        onPick={pickFile}
        onFiles={uploadFiles}
        onOpenDrawer={() => setDrawer(true)}
      />

      {hasDocs && (
        <>
          <div
            className={`sheet-backdrop${source ? ' show' : ''}`}
            onClick={() => setSelected(null)}
          />
          <SourcePanel source={source} claim={claim} onClose={() => setSelected(null)} />
        </>
      )}
    </div>
  );
}
