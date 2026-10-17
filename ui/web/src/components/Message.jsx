import { useEffect, useState } from 'react';
import Icon from './Icon.jsx';
import { AnswerBody } from '../format.jsx';

const STEPS = ['Searching your documents', 'Reading the best passages', 'Writing the answer…'];

// Named steps instead of a bare spinner. The timing is approximate: the server sends the
// whole answer at once, so these steps tell the person that work is happening.
function LoadingSteps() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const timers = [setTimeout(() => setStage(1), 1200), setTimeout(() => setStage(2), 3500)];
    return () => timers.forEach(clearTimeout);
  }, []);
  return (
    <ol className="steps" aria-live="polite">
      {STEPS.slice(0, stage + 1).map((label, i) => (
        <li key={label} className={i < stage ? 'done' : 'current'}>
          {i < stage ? <Icon name="check" size={14} width={2.6} /> : <span className="dot" />}
          {label}
        </li>
      ))}
    </ol>
  );
}

function ErrorCard({ error, onRetry }) {
  const detail = error?.type === 'NetworkError' || error?.status === 429 ? error.message : null;
  return (
    <div className="box box-error" role="alert">
      <p className="box-title">We couldn’t get an answer just now.</p>
      <p>
        {detail ?? 'The problem is on our side, not with your document.'} Your question is still in
        the box.
      </p>
      <div className="row">
        <button className="btn-ghost" onClick={onRetry}>
          Try again
        </button>
      </div>
    </div>
  );
}

function NotFound({ message, onRephrase, onPick }) {
  return (
    <div className="box">
      <p className="eyebrow">NOT FOUND</p>
      <p className="big">I couldn’t find this in the uploaded documents.</p>
      {message.searched?.length > 0 && (
        <p className="muted">Searched: {message.searched.join(', ')}</p>
      )}
      <div className="row">
        <button className="btn-ghost" onClick={() => onRephrase(message.question)}>
          Rephrase my question
        </button>
        <button className="btn-ghost" onClick={onPick}>
          Upload another PDF
        </button>
      </div>
    </div>
  );
}

export default function Message({ message, selected, onChip, onRetry, onRephrase, onPick }) {
  if (message.role === 'user') {
    return (
      <div className="user-msg">
        <p>{message.text}</p>
      </div>
    );
  }

  const { status, answer } = message;
  const passages = answer?.sources.length ?? 0;
  const label =
    status === 'done' && answer.found && passages > 0
      ? `DocuAsk · answered from ${passages} passage${passages === 1 ? '' : 's'}`
      : 'DocuAsk';
  const activeNumber = selected?.messageId === message.id ? selected.number : null;

  return (
    <article className="bot-msg">
      <div className="bot-head">
        <span className="bot-badge">
          <Icon name="doc" size={14} stroke="#fff" width={2.2} />
        </span>
        {label}
      </div>

      {status === 'loading' && <LoadingSteps />}
      {status === 'stopped' && (
        <p className="muted">Answer stopped. Your question is back in the box.</p>
      )}
      {status === 'error' && <ErrorCard error={message.error} onRetry={() => onRetry(message.id)} />}
      {status === 'done' && !answer.found && (
        <NotFound message={message} onRephrase={onRephrase} onPick={onPick} />
      )}
      {status === 'done' && answer.found && (
        <>
          <AnswerBody
            text={answer.answer}
            sources={answer.sources}
            selected={activeNumber}
            onChip={(n) => onChip(message.id, n)}
          />
          {answer.sources.length > 0 && (
            <div className="pills">
              {answer.sources.map((s) => (
                <button
                  key={s.number}
                  className={`source-pill${activeNumber === s.number ? ' active' : ''}`}
                  onClick={() => onChip(message.id, s.number)}
                >
                  <b>{s.number}</b>
                  <span>
                    {s.file_name} · p. {s.page_number}
                  </span>
                </button>
              ))}
            </div>
          )}
          {!answer.cited && (
            <p className="notice notice-warn">
              <Icon name="alert" size={18} />
              <span>This answer has no citation. Check it against your document before relying on it.</span>
            </p>
          )}
        </>
      )}
    </article>
  );
}
