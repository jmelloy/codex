/**
 * @mention parsing shared by the comment composer and its autocomplete dropdown.
 *
 * Mirrors the backend's handle pattern (codex/api/routes/comments.py MENTION_RE)
 * so the frontend and backend agree on what counts as a mention.
 */

// eslint-disable-next-line no-useless-escape
export const MENTION_RE = /(?<!\w)@([A-Za-z0-9_.-]+)/g

/** All distinct @handles referenced in `text`, in first-seen order. */
export function parseMentions(text: string): string[] {
  const seen = new Set<string>()
  for (const match of text.matchAll(MENTION_RE)) {
    const handle = match[1]
    if (handle) seen.add(handle)
  }
  return [...seen]
}

export interface MentionQuery {
  /** Index of the "@" that starts the mention. */
  start: number
  /** Cursor index (end of the partial handle typed so far). */
  end: number
  /** Partial handle typed after "@", used to filter autocomplete candidates. */
  query: string
}

const HANDLE_CHAR_RE = /[A-Za-z0-9_.-]/

/**
 * Find the mention the cursor is currently "inside", if any — i.e. an "@" not
 * preceded by a word character, followed only by handle characters up to the cursor.
 * Returns null once the caret moves past the mention (e.g. a space was typed).
 */
export function findActiveMentionQuery(text: string, cursor: number): MentionQuery | null {
  if (cursor < 0 || cursor > text.length) return null

  let i = cursor
  while (i > 0 && HANDLE_CHAR_RE.test(text[i - 1]!)) i--

  if (i === 0 || text[i - 1] !== "@") return null

  const charBeforeAt = text[i - 2]
  if (charBeforeAt && /\w/.test(charBeforeAt)) return null

  return { start: i - 1, end: cursor, query: text.slice(i, cursor) }
}

/** Replace an active mention query with `@username ` and return the new text + cursor position. */
export function insertMention(
  text: string,
  mentionQuery: MentionQuery,
  username: string,
): { text: string; cursor: number } {
  const before = text.slice(0, mentionQuery.start)
  const after = text.slice(mentionQuery.end)
  const inserted = `@${username} `
  return { text: before + inserted + after, cursor: (before + inserted).length }
}
