import React, { useState, useEffect } from 'react';
import { FileTree } from './components/FileTree';
import { SearchInterface } from './components/SearchInterface';
import { CodeViewer } from './components/CodeViewer';
import { SearchResult, FileNode, OpenedFile } from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function App() {
  const [selectedResult, setSelectedResult] = useState<SearchResult | undefined>();
  const [selectedFile, setSelectedFile] = useState<OpenedFile | null>(null);

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [fileTreeLoading, setFileTreeLoading] = useState(true);
  const [fileTreeError, setFileTreeError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTree = async () => {
      try {
        const res = await fetch(`${API_BASE}/file-tree`);
        if (!res.ok) throw new Error(await res.text());
        const data: FileNode = await res.json();
        setFileTree(data);
      } catch (e: any) {
        setFileTreeError(e?.message ?? "Failed to load file tree");
      } finally {
        setFileTreeLoading(false);
      }
    };
    fetchTree();
  }, []);

  const handleResultSelect = (result: SearchResult) => {
    setSelectedFile(null);
    setSelectedResult(result);
  };

  const handleCloseViewer = () => {
    setSelectedResult(undefined);
    setSelectedFile(null);
  };

  const handleCodeSearch = async (query: string, topK = 15) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ query, top_k: String(topK) });
      const res = await fetch(`${API_BASE}/code-search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const raw = await res.json();
      const items = Array.isArray(raw) ? raw : raw?.result ?? [];
      const normalized: SearchResult[] = items
        .map((item: any) => {
          const rawDistance =
            typeof item?.score === 'number'
              ? item.score
              : item?.score ?? item?.distance ?? 1;
          const distance = Number(rawDistance);
          const similarity = Math.max(0, Math.min(1, 1 - distance));

          return {
            id: String(item?.id ?? item?.metadata?.id ?? ''),
            content: String(item?.content ?? item?.metadata?.context_code ?? ''),
            score: similarity,
            metadata: {
              fileName: String(item?.metadata?.fileName ?? item?.metadata?.context_file_name ?? ''),
              filePath: String(item?.metadata?.filePath ?? item?.metadata?.context_file_path ?? ''),
              language: String(item?.metadata?.language ?? item?.metadata?.context_language ?? ''),
              functionName: item?.metadata?.functionName ?? item?.metadata?.context_name ?? undefined,
              lineStart: Number(item?.metadata?.lineStart ?? item?.metadata?.line_from ?? 0),
              lineEnd: Number(item?.metadata?.lineEnd ?? item?.metadata?.line_to ?? 0),
            },
          };
        })
        .filter(item => item.id && item.content);
      setResults(normalized);
    } catch (e: any) {
      console.error(e);
      setError(e?.message ?? 'Search failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAndOpenFile = async (path: string) => {
    try {
      const res = await fetch(`${API_BASE}/file-content?path=${encodeURIComponent(path)}`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSelectedResult(undefined); // ensure only one mode is active
      setSelectedFile({
        path: data.path,
        language: data.language,
        content: data.content,
      });
    } catch (e) {
      console.error("Failed to fetch file content:", e);
    }
  };

  return (
    <div className="h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 flex overflow-hidden">
      {/* File Tree Sidebar */}
      <div className="w-80 flex-shrink-0">
        {fileTreeLoading && (
          <div className="h-full text-white flex items-center justify-center">
            Loading file tree…
          </div>
        )}
        {fileTreeError && (
          <div className="h-full text-red-400 p-4">
            {fileTreeError}
          </div>
        )}
        {fileTree && <FileTree node={fileTree} onFileClick={fetchAndOpenFile} />}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <SearchInterface
          onResultSelect={handleResultSelect}
          onSearch={handleCodeSearch}
          results={results}
          loading={loading}
          error={error}
        />
      </div>

      {/* Code Viewer Modal */}
      {(selectedResult || selectedFile) && (
        <CodeViewer
          selectedResult={selectedResult}
          selectedFile={selectedFile}
          onClose={handleCloseViewer}
        />
      )}
    </div>
  );
}

export default App;
