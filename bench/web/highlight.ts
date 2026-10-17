/** Mark the query's words in a snippet of a search result, for display as HTML. */

export interface Highlighted {
  html: string;
  marks: number;
}

export function highlight(text: string, query: string): Highlighted {
  const words = query.split(/\s+/).filter((w) => w.length > 0);
  if (words.length === 0) {
    return { html: text, marks: 0 };
  }
  const pattern = new RegExp(`(${words.join("|")})`, "gi");
  let marks = 0;
  const html = text.replace(pattern, (found) => {
    marks += 1;
    return `<mark>${found}</mark>`;
  });
  return { html, marks };
}

/** The first `width` characters around the first match, with an ellipsis where cut. */
export function snippet(text: string, query: string, width = 80): string {
  const first = query.split(/\s+/)[0] ?? "";
  const at = first ? text.toLowerCase().indexOf(first.toLowerCase()) : -1;
  const start = Math.max(0, at - Math.floor(width / 2));
  const cut = text.slice(start, start + width);
  return (start > 0 ? "…" : "") + cut + (start + width < text.length ? "…" : "");
}
