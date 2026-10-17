import { useState } from 'react';

// Drag-and-drop for files. Spread `props` on an element; `over` is true while a file hovers.
export function useDrop(onFiles) {
  const [over, setOver] = useState(false);
  return {
    over,
    props: {
      onDragOver: (e) => {
        e.preventDefault();
        setOver(true);
      },
      onDragLeave: () => setOver(false),
      onDrop: (e) => {
        e.preventDefault();
        setOver(false);
        if (e.dataTransfer.files.length) onFiles(Array.from(e.dataTransfer.files));
      },
    },
  };
}
