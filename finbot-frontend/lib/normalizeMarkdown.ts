/**
 * Fix common LLM markdown issues before rendering.
 * Pipe tables are often collapsed onto a single line: "| a | b | | c | d |"
 */
export function normalizeMarkdown(content: string): string {
    if (!content.includes("|")) {
        return content;
    }

    let text = content;

    // Split collapsed table rows onto separate lines.
    text = text.replace(/\|\s+\|(?=\S)/g, "|\n|");

    // Ensure a blank line before a table when it follows plain text on the previous line.
    text = text.replace(/([^\n|])\n(\|[^\n]+\|)/g, "$1\n\n$2");

    return text;
}
