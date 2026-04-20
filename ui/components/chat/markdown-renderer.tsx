"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  children: string;
}

export function MarkdownRenderer({ children }: MarkdownRendererProps) {
  return (
    <div className="markdown-shell">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre(props) {
            return (
              <pre className="overflow-x-auto rounded-[1.2rem] border border-white/10 bg-[rgba(0,0,0,.42)] p-4 text-[13px] text-[rgb(222,245,255)]" {...props} />
            );
          },
          code(props) {
            const { children: codeChildren, className, ...rest } = props;
            const isInline = !className;
            if (isInline) {
              return (
                <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[0.88em] text-[rgb(176,244,255)]" {...rest}>
                  {codeChildren}
                </code>
              );
            }
            return (
              <code className={className} {...rest}>
                {codeChildren}
              </code>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
