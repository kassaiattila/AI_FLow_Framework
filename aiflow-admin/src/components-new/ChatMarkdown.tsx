/**
 * ChatMarkdown — Renders markdown content in chat messages.
 *
 * Pure TypeScript implementation with no external markdown dependencies.
 * Supports: headers, bold, italic, inline code, code blocks, lists, links.
 */

import { useState, useMemo } from "react";
import { CodeBlock } from "./CodeBlock";

interface ChatMarkdownProps {
  content: string;
}

/** Parse a markdown string into an array of typed blocks. */
function parseMarkdown(raw: string): Block[] {
  const blocks: Block[] = [];
  const lines = raw.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.trimStart().startsWith("```")) {
      const lang = line.trimStart().slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trimStart().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      blocks.push({ type: "code", language: lang, content: codeLines.join("\n") });
      i++; // skip closing ```
      continue;
    }

    // Header
    const headerMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (headerMatch) {
      const level = headerMatch[1].length as 1 | 2 | 3;
      blocks.push({ type: "header", level, content: headerMatch[2] });
      i++;
      continue;
    }

    // Unordered list item
    if (line.match(/^\s*[-*+]\s+/)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^\s*[-*+]\s+/)) {
        items.push(lines[i].replace(/^\s*[-*+]\s+/, ""));
        i++;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    // Ordered list item
    if (line.match(/^\s*\d+\.\s+/)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^\s*\d+\.\s+/)) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      blocks.push({ type: "ordered_list", items });
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph (collect consecutive non-empty lines)
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].trimStart().startsWith("```") &&
      !lines[i].match(/^#{1,3}\s+/) &&
      !lines[i].match(/^\s*[-*+]\s+/) &&
      !lines[i].match(/^\s*\d+\.\s+/)
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push({ type: "paragraph", content: paraLines.join(" ") });
    }
  }

  return blocks;
}

type Block =
  | { type: "code"; language: string; content: string }
  | { type: "header"; level: 1 | 2 | 3; content: string }
  | { type: "list"; items: string[] }
  | { type: "ordered_list"; items: string[] }
  | { type: "paragraph"; content: string };

/** Render inline markdown (bold, italic, code, links) to JSX. */
function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Pattern: **bold**, *italic*, `code`, [text](url)
  const pattern = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = pattern.exec(text)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    if (match[2]) {
      // Bold
      nodes.push(
        <strong key={key++} className="font-semibold">
          {match[2]}
        </strong>
      );
    } else if (match[3]) {
      // Italic
      nodes.push(
        <em key={key++} className="italic">
          {match[3]}
        </em>
      );
    } else if (match[4]) {
      // Inline code
      nodes.push(
        <code
          key={key++}
          className="rounded bg-gray-100 px-1 py-0.5 text-sm font-mono dark:bg-gray-800"
        >
          {match[4]}
        </code>
      );
    } else if (match[5] && match[6]) {
      // Link
      nodes.push(
        <a
          key={key++}
          href={match[6]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-600 underline hover:text-indigo-800 dark:text-indigo-400"
        >
          {match[5]}
        </a>
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length > 0 ? nodes : [text];
}

const HEADER_CLASSES: Record<number, string> = {
  1: "text-xl font-bold mb-2 mt-4",
  2: "text-lg font-semibold mb-1.5 mt-3",
  3: "text-base font-semibold mb-1 mt-2",
};

export function ChatMarkdown({ content }: ChatMarkdownProps) {
  const blocks = useMemo(() => parseMarkdown(content), [content]);

  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {blocks.map((block, idx) => {
        switch (block.type) {
          case "code":
            return <CodeBlock key={idx} code={block.content} language={block.language} />;

          case "header":
            return (
              <div key={idx} className={HEADER_CLASSES[block.level]}>
                {renderInline(block.content)}
              </div>
            );

          case "list":
            return (
              <ul key={idx} className="list-disc pl-5 space-y-0.5">
                {block.items.map((item, j) => (
                  <li key={j}>{renderInline(item)}</li>
                ))}
              </ul>
            );

          case "ordered_list":
            return (
              <ol key={idx} className="list-decimal pl-5 space-y-0.5">
                {block.items.map((item, j) => (
                  <li key={j}>{renderInline(item)}</li>
                ))}
              </ol>
            );

          case "paragraph":
            return (
              <p key={idx}>{renderInline(block.content)}</p>
            );

          default:
            return null;
        }
      })}
    </div>
  );
}
