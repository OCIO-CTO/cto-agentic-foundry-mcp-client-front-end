import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import remarkGfm from "remark-gfm";
import { memo } from "react";

/**
 * Markdown text component for rendering AI assistant messages
 * Supports GitHub Flavored Markdown with code blocks, tables, etc.
 */
const MarkdownTextImpl = () => {
  return (
    <MarkdownTextPrimitive
      remarkPlugins={[remarkGfm]}
      className="markdown-content"
    />
  );
};

export const MarkdownText = memo(MarkdownTextImpl);
