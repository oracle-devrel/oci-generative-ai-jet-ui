import React, { useState, useRef } from 'react';
import { Search, Upload } from 'lucide-react';
import { ViewToggle } from './ViewToggle';

interface SearchBarProps {
  onTextSearch: (query: string) => void;
  onImageSearch: (file: File) => void;
  searchQuery: string;
  searchMode: 'text' | 'image';
  onSearchModeChange: (mode: 'text' | 'image') => void;
  viewMode: 'grid' | 'list';
  onViewModeChange: (mode: 'grid' | 'list') => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ 
  onTextSearch, 
  onImageSearch, 
  searchQuery,
  searchMode,
  onSearchModeChange,
  viewMode,
  onViewModeChange
}) => {
  const [query, setQuery] = useState(searchQuery);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleTextSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onTextSearch(query);
  };

  const handleImageUpload = (file: File) => {
    if (file && file.type.startsWith('image/')) {
      onImageSearch(file);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleImageUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="mb-8 space-y-4">
      {/* Search Mode Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <button
            onClick={() => onSearchModeChange('text')}
            className={`flex items-center gap-2 px-1 py-2 text-sm font-medium border-b-2 transition-colors ${
              searchMode === 'text'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <Search className="w-4 h-4" />
            Text
          </button>
          <button
            onClick={() => onSearchModeChange('image')}
            className={`flex items-center gap-2 px-1 py-2 text-sm font-medium border-b-2 transition-colors ${
              searchMode === 'image'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Image
          </button>
        </div>

        <ViewToggle viewMode={viewMode} onViewModeChange={onViewModeChange} />
      </div>

      {/* Search Input */}
      {searchMode === 'text' ? (
        <form onSubmit={handleTextSearch}>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search for products..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </form>
      ) : (
        <div
          className={`relative border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragActive 
              ? 'border-blue-400 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileInputChange}
            className="hidden"
          />
          
          <div className="space-y-4">
            <div className="mx-auto w-16 h-16 text-gray-400">
              <Upload className="w-full h-full" />
            </div>
            
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Drop an image here or click to upload
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                PNG, JPG, GIF up to 10MB
              </p>
              
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                <Upload className="w-4 h-4" />
                Choose File
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
