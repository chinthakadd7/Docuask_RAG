import { Fragment } from 'react';

// Turns the model's answer text into paragraphs, bullets, **bold** and clickable [1] chips.
const TOKEN = /(\*\*[^*]+\*\*|\[\d+\])/g;

function inline(text, { sources, selected, onChip }, keyPrefix) {
  return text
    .split(TOKEN)
    .filter(Boolean)
    .map((part, i) => {
      const key = `${keyPrefix}-${i}`;
      const cite = part.match(/^\[(\d+)\]$/);
      if (cite) {
        const number = Number(cite[1]);
        if (!sources.some((s) => s.number === number)) return null; // unknown number: show nothing
        return (
          <button
            key={key}
            type="button"
            className={`chip${selected === number ? ' chip-active' : ''}`}
            onClick={() => onChip(number)}
            aria-label={`Show source ${number}`}
          >
            {number}
          </button>
        );
      }
      if (part.startsWith('**')) return <strong key={key}>{part.slice(2, -2)}</strong>;
      return <Fragment key={key}>{part}</Fragment>;
    });
}

export function AnswerBody({ text, sources, selected, onChip }) {
  const ctx = { sources, selected, onChip };
  const blocks = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const bullet = line.match(/^[*-]\s+(.*)$/);
    const last = blocks[blocks.length - 1];
    if (bullet) {
      if (last?.type === 'ul') last.items.push(bullet[1]);
      else blocks.push({ type: 'ul', items: [bullet[1]] });
    } else {
      blocks.push({ type: 'p', text: line });
    }
  }

  return (
    <div className="answer">
      {blocks.map((block, i) =>
        block.type === 'ul' ? (
          <ul key={i}>
            {block.items.map((item, j) => (
              <li key={j}>{inline(item, ctx, `${i}-${j}`)}</li>
            ))}
          </ul>
        ) : (
          <p key={i}>{inline(block.text, ctx, String(i))}</p>
        ),
      )}
    </div>
  );
}
