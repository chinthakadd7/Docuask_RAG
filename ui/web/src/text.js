// Small text helpers with no React in them, so they are easy to test.

const words = (text) => new Set(text.toLowerCase().match(/[a-z0-9]{4,}/g) ?? []);

// The part of the answer that cites source number `n` (markers and **bold** removed).
export function claimFor(answerText, n) {
  const marker = `[${n}]`;
  return answerText
    .split(/(?<=[.!?\n])\s+/)
    .filter((sentence) => sentence.includes(marker))
    .join(' ')
    .replace(/\[\d+\]|\*\*/g, '');
}

// Splits a passage into sentences and flags the ones that support the claim,
// by how many of their longer words also appear in the claim.
export function splitPassage(passage, claim) {
  const claimWords = words(claim);
  return passage
    .split(/(?<=[.!?])\s+/)
    .filter(Boolean)
    .map((text) => {
      const sentenceWords = words(text);
      let shared = 0;
      sentenceWords.forEach((w) => {
        if (claimWords.has(w)) shared += 1;
      });
      return { text, highlight: shared >= 2 && shared / sentenceWords.size >= 0.4 };
    });
}
