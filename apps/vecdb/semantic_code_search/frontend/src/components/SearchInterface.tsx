import React, { useState, useRef, useEffect } from 'react';
import { Search, Code, Clock, Star, Database } from 'lucide-react';
import { SearchResult } from '../types';
import { VectorDBInfo } from './VectorDBInfo';

interface SearchInterfaceProps {
  onResultSelect: (result: SearchResult) => void;
  onSearch: (query: string, topK?: number) => Promise<void> | void;
  results: SearchResult[];
  loading: boolean;
  error: string | null;
}

const searchSuggestions = [
  "create a RunnableSequence that maps then chains steps",
  "format a ChatPromptTemplate with input variables",
  "parse LLM output into JSON with StrOutputParser",
  "manage chat history with InMemoryChatMessageHistory",
  "work with AIMessage and HumanMessage message types"
];

export const SearchInterface: React.FC<SearchInterfaceProps> = ({
  onResultSelect,
  onSearch,
  results,
  loading,
  error
}) => {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(15);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedResult, setSelectedResult] = useState<SearchResult | null>(null);
  const [showVectorDBInfo, setShowVectorDBInfo] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = async (searchQuery?: string) => {
    const queryToSearch = searchQuery || query;
    if (!queryToSearch.trim()) return;
    setShowSuggestions(false);
    await onSearch(queryToSearch, topK);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    handleSearch(suggestion);
  };

  const handleResultClick = (result: SearchResult) => {
    setSelectedResult(result);
    onResultSelect(result);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-start pt-20 px-6">
      {/* Main Search Section */}
      <div className="w-full max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            LangChain Semantic Code Search
          </h1>
          <p className="text-xl text-blue-100 max-w-2xl mx-auto">
            Search your codebase with natural language using LangChain and vector embeddings
          </p>
          <div className="mt-2 text-sm text-blue-200">
            Powered by Oracle AI Database
          </div>
          <button
            onClick={() => setShowVectorDBInfo(true)}
            className="mt-4 inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm text-white px-4 py-2 rounded-lg hover:bg-white/30 transition-colors"
          >
            <Database className="w-4 h-4" />
            View Vector DB Info
          </button>
        </div>

        {/* Search Bar */}
        <div ref={searchRef} className="relative mb-8">
          <div className="relative">
            <Search className="absolute left-6 top-1/2 transform -translate-y-1/2 text-gray-400 w-6 h-6" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              onFocus={() => setShowSuggestions(true)}
              placeholder="Describe the code you're looking for..."
              className="w-full pl-16 pr-6 py-6 text-lg bg-white/95 backdrop-blur-sm border-0 rounded-2xl shadow-2xl focus:ring-4 focus:ring-blue-300/50 focus:outline-none transition-all duration-300"
            />

            {/* top_k control */}
            <input
              type="number"
              value={topK}
              min={1}
              onChange={(e) => setTopK(Number(e.target.value))}
              title="top_k"
              className="absolute right-36 top-1/2 transform -translate-y-1/2 bg-white/80 text-black px-3 py-2 w-20 rounded-lg mr-2"
            />

            <button
              onClick={() => handleSearch()}
              disabled={loading || !query.trim()}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          {/* Search Suggestions */}
          {showSuggestions && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-sm rounded-xl shadow-2xl border border-white/20 overflow-hidden z-50">
              <div className="p-4 border-b border-gray-100">
                <h3 className="text-sm font-medium text-gray-600 mb-3">Try these examples:</h3>
                <div className="space-y-2">
                  {searchSuggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="w-full text-left px-4 py-3 text-gray-700 hover:bg-blue-50 rounded-lg transition-colors flex items-center gap-3"
                    >
                      <Code className="w-4 h-4 text-blue-500" />
                      <span>{suggestion}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="text-red-400 mb-4">{error}</div>
        )}

        {/* Search Results */}
        {results.length > 0 && (
          <div className="max-h-[60vh] overflow-y-auto">
          <div className="flex items-center gap-3 mb-6">
            <Star className="w-5 h-5 text-yellow-400" />
            <h2 className="text-xl font-semibold text-white">
              Found {results.length} matching code snippets
            </h2>
          </div>
          
          <div className="space-y-4 pb-24">
            {results.map((result, index) => (
              <div
                key={result.id}
                onClick={() => handleResultClick(result)}
                className={`bg-white/95 backdrop-blur-sm rounded-xl p-6 shadow-lg hover:shadow-xl cursor-pointer transition-all duration-300 border-2 ${
                  selectedResult?.id === result.id 
                    ? 'border-blue-400 ring-4 ring-blue-200/50' 
                    : 'border-transparent hover:border-blue-200'
                }`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-3 py-1 rounded-full">
                        #{index + 1}
                      </span>
                      <h3 className="font-semibold text-gray-900">
                        {result.metadata.functionName || 'Code Block'}
                      </h3>
                      <span className="text-xs text-gray-500">
                        {result.metadata.language}
                      </span>
                    </div>
                    <div className="text-sm text-gray-600 mb-3">
                      <span className="font-medium">{result.metadata.fileName}</span>
                      <span className="mx-2">•</span>
                      <span>Lines {result.metadata.lineStart}-{result.metadata.lineEnd}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-blue-600">
                      {(Number(result.score ?? 0) * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-500">similarity</div>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4 overflow-x-auto">
                  <pre className="text-sm text-gray-800 font-mono leading-relaxed">
                    <code>{result.content}</code>
                  </pre>
                </div>
                
                <div className="flex items-center justify-between mt-4">
                  <div className="flex gap-2">
                    <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                      {result.metadata.language}
                    </span>
                    <span className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded">
                      {result.metadata.fileName}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Click to view full code
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        )}

        {/* Empty State */}
        {!loading && results.length === 0 && query && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-white mb-2">No results found</h3>
            <p className="text-blue-100">Try a different search query or use one of the suggested examples above</p>
          </div>
        )}
      </div>

      {/* Vector DB Info Modal */}
      <VectorDBInfo 
        isOpen={showVectorDBInfo} 
        onClose={() => setShowVectorDBInfo(false)} 
      />
    </div>
  );
};
