import Icon from './Icon.jsx';
import { useDrop } from '../useDrop.js';

function DocItem({ doc, onDelete }) {
  const ready = doc.status === 'ready';
  return (
    <li className="doc">
      <Icon name="doc" size={20} stroke="var(--muted)" />
      <span className="doc-name" title={doc.name}>
        {doc.name}
      </span>
      {ready ? (
        <button className="icon-btn" onClick={() => onDelete(doc)} aria-label={`Delete ${doc.name}`}>
          <Icon name="trash" size={18} stroke="var(--muted)" />
        </button>
      ) : (
        <span />
      )}
      <span className="doc-status">
        {ready ? (
          <>
            <Icon name="check" size={13} width={2.6} /> Ready to ask
          </>
        ) : (
          'Reading pages…'
        )}
      </span>
      {!ready && <span className="bar" />}
    </li>
  );
}

export default function Sidebar({ docs, notices, maxMb, open, onPick, onFiles, onDelete, onDismiss, onClose }) {
  const drop = useDrop(onFiles);
  return (
    <aside className={`sidebar${open ? ' open' : ''}`}>
      <div className="logo">
        <Icon name="doc" size={28} stroke="var(--teal)" />
        <span>DocuAsk</span>
        <button className="icon-btn drawer-close" onClick={onClose} aria-label="Close documents">
          <Icon name="close" size={22} />
        </button>
      </div>

      <button className="btn-primary" onClick={onPick}>
        <Icon name="upload" size={18} stroke="#fff" width={2} /> Upload a PDF
      </button>
      <div className={`dropzone${drop.over ? ' over' : ''}`} {...drop.props}>
        <span>or drop a file here</span>
        <span>PDF only · up to {maxMb} MB</span>
      </div>

      {notices.map((n) => (
        <div key={n.id} className={`notice notice-${n.tone}`} role="status">
          <Icon name={n.tone === 'info' ? 'info' : 'alert'} size={18} />
          <span>{n.text}</span>
          <button className="icon-btn" onClick={() => onDismiss(n.id)} aria-label="Dismiss">
            <Icon name="close" size={16} />
          </button>
        </div>
      ))}

      <h2 className="eyebrow">YOUR DOCUMENTS</h2>
      {docs.length === 0 ? (
        <p className="muted">
          Nothing here yet. Documents you upload will be listed with their status.
        </p>
      ) : (
        <ul className="doc-list">
          {docs.map((doc) => (
            <DocItem key={doc.id} doc={doc} onDelete={onDelete} />
          ))}
        </ul>
      )}

      <p className="footnote">
        Page numbers match the PDF’s own page count (page 1 is the first page), not the number
        printed on the page.
      </p>
    </aside>
  );
}
