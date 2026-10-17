import { useState } from 'react';
import Icon from './Icon.jsx';
import { splitPassage } from '../text.js';

// Right-hand panel on wide screens, bottom sheet on phones and tablets (see styles.css).
export default function SourcePanel({ source, claim, onClose }) {
  const [copied, setCopied] = useState(false);

  async function copyCitation() {
    try {
      await navigator.clipboard.writeText(`${source.file_name}, p. ${source.page_number}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked by the browser: nothing to do
    }
  }

  return (
    <aside className={`source-panel${source ? ' open' : ''}`} aria-label="Source viewer">
      {!source ? (
        <p className="placeholder">
          Select a numbered citation in an answer to see the exact passage it came from.
        </p>
      ) : (
        <>
          <div className="sp-top">
            <p className="eyebrow">SOURCE {source.number}</p>
            <button className="icon-btn sheet-close" onClick={onClose} aria-label="Close source">
              <Icon name="close" size={22} />
            </button>
          </div>
          <h2 className="sp-file">{source.file_name}</h2>
          <p className="muted">
            PDF page {source.page_number} · passage {source.chunk_index + 1}
          </p>
          <div className="passage">
            …
            {splitPassage(source.text, claim).map((part, i) => (
              <span key={i}>
                {part.highlight ? <mark>{part.text}</mark> : part.text}{' '}
              </span>
            ))}
            …
          </div>
          <div className="row">
            <button className="btn-ghost" onClick={copyCitation}>
              <Icon name="copy" size={16} /> {copied ? 'Copied' : 'Copy citation'}
            </button>
          </div>
          <p className="footnote">
            Showing the exact passage the answer was built from. Highlighted text supports the claim.
          </p>
        </>
      )}
    </aside>
  );
}
