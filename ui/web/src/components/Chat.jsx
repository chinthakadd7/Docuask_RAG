import { useEffect, useRef } from 'react';
import Icon from './Icon.jsx';
import Message from './Message.jsx';
import { useDrop } from '../useDrop.js';

const STARTERS = ['What is the notice period?', 'Summarise section 3', 'When does the contract end?'];

function EmptyState({ hasDocs, canAsk, maxMb, onPick, onFiles, onSend }) {
  const drop = useDrop(onFiles);

  if (hasDocs) {
    return (
      <div className="empty">
        <h2>{canAsk ? 'Your documents are ready.' : 'Reading your document…'}</h2>
        <p className="lead">
          {canAsk
            ? 'Try one of these, or type your own question below.'
            : 'You can ask as soon as the pages have been read.'}
        </p>
        <div className="starters">
          {STARTERS.map((q) => (
            <button key={q} className="pill" disabled={!canAsk} onClick={() => onSend(q)}>
              {q}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="empty">
      <h2>Ask a question. Get the answer, with the page it came from.</h2>
      <p className="lead">
        Upload a PDF and DocuAsk answers only from what is written in it. Every claim links to the
        exact passage, so you can check it in one click.
      </p>
      <div className={`bigdrop${drop.over ? ' over' : ''}`} {...drop.props}>
        <Icon name="upload" size={28} stroke="var(--teal)" />
        <strong>Drop a PDF here</strong>
        <button className="btn-primary" onClick={onPick}>
          Browse files
        </button>
        <small>PDF only · up to {maxMb} MB · text-based PDFs (scans are not supported yet)</small>
      </div>
      <div className="cards">
        <div className="box">
          <h3>Good at</h3>
          <p>Finding specific facts, numbers, dates, and policies, and showing where they appear.</p>
        </div>
        <div className="box">
          <h3>Will say so when</h3>
          <p>The answer is not in your documents. It will not guess or use outside knowledge.</p>
        </div>
      </div>
      <p className="eyebrow">Questions people ask once a document is ready</p>
      <div className="starters">
        {STARTERS.map((q) => (
          <button key={q} className="pill" disabled>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Chat({
  docs, readyDocs, messages, selected, scope, setScope, draft, setDraft, busy, composerRef,
  maxMb, onSend, onStop, onRetry, onRephrase, onChip, onPick, onFiles, onOpenDrawer,
}) {
  const scrollRef = useRef(null);
  const hasDocs = docs.length > 0;
  const canAsk = readyDocs.length > 0;
  const showEmpty = !hasDocs || messages.length === 0;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  // Shrink the box back to one line after sending.
  useEffect(() => {
    const el = composerRef.current;
    if (el && draft === '') el.style.height = 'auto';
  }, [draft, composerRef]);

  return (
    <section className="chat">
      <header className="chat-header">
        <button className="docs-btn" onClick={onOpenDrawer}>
          {docs.length} document{docs.length === 1 ? '' : 's'}
        </button>
        <h1 className="title-desktop">Ask your documents</h1>
        <span className="title-mobile">DocuAsk</span>
        {hasDocs && (
          <label className="scope">
            <span>Search in</span>
            <span className="select-wrap">
              <select value={scope} onChange={(e) => setScope(e.target.value)} disabled={!canAsk}>
                <option value="all">All ready documents ({readyDocs.length})</option>
                {readyDocs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <Icon name="chevron" size={16} />
            </span>
          </label>
        )}
      </header>

      <div className="messages" ref={scrollRef}>
        {showEmpty ? (
          <EmptyState
            hasDocs={hasDocs}
            canAsk={canAsk}
            maxMb={maxMb}
            onPick={onPick}
            onFiles={onFiles}
            onSend={onSend}
          />
        ) : (
          messages.map((m) => (
            <Message
              key={m.id}
              message={m}
              selected={selected}
              onChip={onChip}
              onRetry={onRetry}
              onRephrase={onRephrase}
              onPick={onPick}
            />
          ))
        )}
      </div>

      <div className="composer-wrap">
        <div className="composer">
          <textarea
            ref={composerRef}
            rows={1}
            value={draft}
            disabled={!canAsk}
            placeholder={canAsk ? 'Ask a question about your documents' : 'Upload a PDF to start asking'}
            aria-label="Your question"
            onChange={(e) => setDraft(e.target.value)}
            onInput={(e) => {
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                onSend();
              }
            }}
          />
          {busy ? (
            <button className="send stop" onClick={onStop} aria-label="Stop answering">
              <Icon name="stop" size={18} />
            </button>
          ) : (
            <button
              className="send"
              onClick={() => onSend()}
              disabled={!canAsk || !draft.trim()}
              aria-label="Send question"
            >
              <Icon name="send" size={20} stroke="#fff" width={2} />
            </button>
          )}
        </div>
        <p className="disclaimer">
          Answers use only your uploaded PDFs. Check the sources before you rely on them.
        </p>
      </div>
    </section>
  );
}
