import React from 'react';
import { Copy, X, Code } from 'lucide-react';
import { SearchResult, OpenedFile } from '../types';
//import './highlight.css';

// Utility to highlight lines
// function escapeHtml(unsafe: string): string {
//   return unsafe
//     .replace(/&/g, "&amp;")
//     .replace(/</g, "&lt;")
//     .replace(/>/g, "&gt;")
//     .replace(/"/g, "&quot;")
//     .replace(/'/g, "&#039;");
// }

// function highlightLines(code: string, start: number, end: number): string {
//   const lines = code.split('\n');
//   return lines
//     .map((line, idx) => {
//       const lineNum = idx + 1;
//       const escaped = escapeHtml(line);
//       if (lineNum >= start && lineNum <= end) {
//         return `<strong>${escaped}</strong>`;  // 🔥 BOLD MATCHING LINES
//       }
//       return escaped;
//     })
//     .join('\n');
// }

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
// Default context window for "Reveal" (lines before/after the match)
const CONTEXT_PRE = 10;
const CONTEXT_POST = 10;
const CONTEXT_STEP = 10; // How many lines to add per click

type CodeViewerProps = {
  selectedResult?: SearchResult;
  selectedFile?: OpenedFile | null;
  onClose: () => void;
};

export const CodeViewer: React.FC<CodeViewerProps> = ({
  selectedResult,
  selectedFile,
  onClose
}) => {
  const [expandedContent, setExpandedContent] = React.useState<string | null>(null);
  const [loadingContext, setLoadingContext] = React.useState(false);
  const [preLines, setPreLines] = React.useState<number>(CONTEXT_PRE);
  const [postLines, setPostLines] = React.useState<number>(CONTEXT_POST);
  const [isFullFile, setIsFullFile] = React.useState<boolean>(false);
  const [fullFileMeta, setFullFileMeta] = React.useState<{ path: string; language?: string } | null>(null);
  const [snippetContext, setSnippetContext] = React.useState<string | null>(null);

  const isFromSearch = !!selectedResult;

  if (!isFromSearch && !selectedFile) return null;

  const content = isFromSearch
    ? (expandedContent ?? selectedResult!.content)
    : (selectedFile?.content ?? '');

  const language = isFullFile
    ? (fullFileMeta?.language ?? (isFromSearch ? selectedResult!.metadata.language : (selectedFile?.language ?? 'text')))
    : (isFromSearch ? selectedResult!.metadata.language : (selectedFile?.language ?? 'text'));

  const title = isFullFile
    ? (fullFileMeta?.path?.split('/').pop() ?? (isFromSearch ? selectedResult!.metadata.fileName : (selectedFile?.path?.split('/').pop() ?? 'File')))
    : (isFromSearch ? (selectedResult!.metadata.functionName || 'Code Block') : (selectedFile?.path?.split('/').pop() ?? 'File'));

  const subtitle = isFullFile
    ? (fullFileMeta?.path ?? (isFromSearch ? selectedResult!.metadata.filePath : (selectedFile?.path ?? '')))
    : (isFromSearch
      ? `${selectedResult!.metadata.fileName} • ${selectedResult!.metadata.filePath} • Lines ${selectedResult!.metadata.lineStart}-${selectedResult!.metadata.lineEnd}`
      : (selectedFile?.path ?? ''));

  const score = isFromSearch ? selectedResult!.score : undefined;

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };
  const handleRevealContext = async () => {
    if (!selectedResult) return;

    setLoadingContext(true);
    try {
      const params = new URLSearchParams({
        path: selectedResult.metadata.filePath,
        start: String(selectedResult.metadata.lineStart),
        end: String(selectedResult.metadata.lineEnd),
      });
      // Request a wider context window from the backend
      params.set('pre', String(preLines));
      params.set('post', String(postLines));
      const res = await fetch(`${API_BASE}/code-context?${params.toString()}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setExpandedContent(data.context);
      setSnippetContext(data.context);
    } catch (err: any) {
      console.error("Failed to fetch context:", err);
    } finally {
      setLoadingContext(false);
    }
  };

  const handleOpenFullFile = async () => {
    if (!selectedResult) return;
    setLoadingContext(true);
    try {
      // Preserve current snippet or expanded context so we can return later
      setSnippetContext(expandedContent ?? selectedResult.content);
      const params = new URLSearchParams({
        path: selectedResult.metadata.filePath,
      });
      const res = await fetch(`${API_BASE}/file-content?${params.toString()}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setExpandedContent(data.content);
      setIsFullFile(true);
      setFullFileMeta({ path: data.path, language: data.language });
    } catch (err) {
      console.error('Failed to open full file:', err);
    } finally {
      setLoadingContext(false);
    }
  };

  const fetchWithWindow = async (pre: number, post: number) => {
    if (!selectedResult) return;
    setLoadingContext(true);
    try {
      const params = new URLSearchParams({
        path: selectedResult.metadata.filePath,
        start: String(selectedResult.metadata.lineStart),
        end: String(selectedResult.metadata.lineEnd),
        pre: String(pre),
        post: String(post),
      });
      const res = await fetch(`${API_BASE}/code-context?${params.toString()}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setExpandedContent(data.context);
      setSnippetContext(data.context);
      setPreLines(pre);
      setPostLines(post);
    } catch (err) {
      console.error('Failed to extend context:', err);
    } finally {
      setLoadingContext(false);
    }
  };

  const handleShowMoreAbove = async () => {
    const nextPre = preLines + CONTEXT_STEP;
    await fetchWithWindow(nextPre, postLines);
  };

  const handleShowMoreBelow = async () => {
    const nextPost = postLines + CONTEXT_STEP;
    await fetchWithWindow(preLines, nextPost);
  };

  // Reset reveal state when switching selection
  React.useEffect(() => {
    setExpandedContent(null);
    setPreLines(CONTEXT_PRE);
    setPostLines(CONTEXT_POST);
    setIsFullFile(false);
    setFullFileMeta(null);
    setSnippetContext(null);
  }, [selectedResult?.id, selectedFile?.path]);


  // Prepare line numbers and optional highlighting for render
  const renderText = expandedContent ?? content;
  let startLine = 1;
  if (isFromSearch) {
    const absStart = Number(selectedResult!.metadata.lineStart || 0);
    if (isFullFile) {
      startLine = 1;
    } else if (expandedContent) {
      startLine = Math.max(1, absStart - preLines);
    } else {
      startLine = Math.max(1, absStart);
    }
  } else if (selectedFile) {
    startLine = 1;
  }

  const lineCount = (renderText?.split('\n') || []).length;
  const lineNumbers = Array.from({ length: lineCount }, (_, i) => String(startLine + i)).join('\n');

  const shouldHighlight = !!(isFromSearch && (expandedContent || isFullFile));
  let codeHtml: string | null = null;
  if (shouldHighlight) {
    try {
      const absStart = Number(selectedResult!.metadata.lineStart || 0);
      const absEnd = Number(selectedResult!.metadata.lineEnd || 0);
      const windowStart = isFullFile ? 1 : Math.max(1, absStart - preLines);
      codeHtml = renderText
        .split('\n')
        .map((line, idx) => {
          const absoluteLine = windowStart + idx;
          const escaped = line
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");
          if (absStart > 0 && absoluteLine >= absStart && absoluteLine <= absEnd) {
            return `<mark style=\"background:#fde68a; padding:0 2px;\">${escaped}</mark>`;
          }
          return escaped;
        })
        .join('\n');
    } catch {
      codeHtml = null;
    }
  }

  
  
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Code className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {title}
                </h3>
                {subtitle && (
                  <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 mt-1">
                    <span>{subtitle}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-3">
              {typeof score === 'number' && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-600">
                    {(score * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500">similarity</div>
                </div>
              )}
              <button
                onClick={() => handleCopy(content)}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Copy to clipboard"
              >
                <Copy className="w-5 h-5" />
              </button>
              <button
                onClick={onClose}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Close"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>

        {/* Code Content */}
        <div className="p-6 overflow-auto max-h-[60vh]">
          <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex gap-2">
                <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-3 py-1 rounded-full">
                  {language}
                </span>
                {isFromSearch && (
                  <span className="inline-block bg-gray-100 text-gray-800 text-xs font-medium px-3 py-1 rounded-full">
                    {selectedResult!.metadata.fileName}
                  </span>
                )}
              </div>
              {isFromSearch && (
                <div className="flex items-center gap-3">
                  {isFullFile && (
                    <button
                      onClick={() => {
                        setIsFullFile(false);
                        setExpandedContent(snippetContext);
                      }}
                      disabled={loadingContext}
                      className="text-blue-600 hover:underline text-sm"
                      title="Back to matched snippet"
                    >
                      Back to snippet
                    </button>
                  )}
                  {!isFullFile && (
                    <button
                      onClick={handleOpenFullFile}
                      disabled={loadingContext}
                      className="text-blue-600 hover:underline text-sm"
                      title="Open full file"
                    >
                      Open full file
                    </button>
                  )}
                  {!isFullFile && (
                    <>
                      <button
                        onClick={handleRevealContext}
                        disabled={loadingContext}
                        className="text-blue-600 hover:underline text-sm flex items-center gap-1"
                        title="Reveal more context"
                      >
                        {loadingContext ? "Loading..." : <><svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> Reveal</>}
                      </button>
                      {expandedContent && (
                        <>
                          <button
                            onClick={handleShowMoreAbove}
                            disabled={loadingContext}
                            className="text-blue-600 hover:underline text-sm"
                            title="Expand above context"
                          >
                            Expand above
                          </button>
                          <button
                            onClick={handleShowMoreBelow}
                            disabled={loadingContext}
                            className="text-blue-600 hover:underline text-sm"
                            title="Expand below context"
                          >
                            Expand below
                          </button>
                        </>
                      )}
                    </>
                  )}
                </div>
              )}
  

            </div>

            <div className="flex text-sm font-mono leading-relaxed">
              <pre className="text-right pr-4 border-r border-gray-200 select-none text-gray-400">
                <code>{lineNumbers}</code>
              </pre>
              <pre className="pl-4 overflow-x-auto flex-1 text-gray-800">
                {codeHtml ? (
                  <code dangerouslySetInnerHTML={{ __html: codeHtml }} />
                ) : (
                  <code>{renderText}</code>
                )}
              </pre>
            </div>


          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              {isFromSearch ? (
                <>
                  <strong>Context:</strong> This code snippet matches your search query with{' '}
                  {(score! * 100).toFixed(1)}% similarity
                </>
              ) : (
                <>
                <strong>Viewing file:</strong> {selectedFile?.path}
                </>
              )}
            </div>
            <button
              onClick={onClose}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
