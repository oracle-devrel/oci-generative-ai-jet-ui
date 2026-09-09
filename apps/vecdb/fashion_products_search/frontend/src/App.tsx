import React, { useState, useEffect } from 'react';
import { Database, Cpu, Filter, Zap } from 'lucide-react';
import SearchInterface from './components/SearchInterface';
import FilterPanel from './components/FilterPanel';
import ResultsGrid from './components/ResultsGrid';
import { SearchResult, SearchFilters } from './types/product';
import { vectorDB } from './services/vectorDatabase';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function buildVecdbFilter(filters: SearchFilters) {
  const filter: Record<string, string> = {};
  if (filters.gender) {
    filter.gender = filters.gender;
  }
  if (filters.masterCategory) {
    filter.masterCategory = filters.masterCategory;
  }
  return Object.keys(filter).length ? filter : undefined;
}

function App() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [filterOptions, setFilterOptions] = useState({
    genders: [] as string[],
    masterCategories: [] as string[],
  });

  useEffect(() => {
    // Initialize filter options
    const options = vectorDB.getFilterOptions();
    setFilterOptions(options);
  }, []);

  const handleTextSearch = async (query: string, topK: number) => {
    setLoading(true);
    try {
      const body = {
        query,
        top_k: topK,
        filters: buildVecdbFilter(filters),
      };
      const res = await fetch(`${API_BASE}/search/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results as SearchResult[]);
      console.log('✅ /search/text ok');
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleImageSearch = async (imageFile: File, topK: number) => {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', imageFile);
      fd.append('top_k', String(topK));
      const f = buildVecdbFilter(filters);
      if (f) fd.append('filters', JSON.stringify(f));

      const res = await fetch(`${API_BASE}/search/image`, {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(data.results as SearchResult[]);
      console.log('✅ /search/image ok');
    } catch (error) {
      console.error('Image search error:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 via-gray-200 to-gray-300">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Database className="text-blue-600" size={32} />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Fashion Recommendation
                </h1>
                <p className="text-sm text-gray-600">
                  Vector Database Demo 
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-6 text-sm">
              <div className="flex items-center space-x-2">
                <Cpu className="text-green-600" size={16} />
                <span className="text-gray-700">Vector Search</span>
              </div>
              <div className="flex items-center space-x-2">
                <Filter className="text-purple-600" size={16} />
                <span className="text-gray-700">Smart Filtering</span>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="text-orange-600" size={16} />
                <span className="text-gray-700">Real-time Results</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SearchInterface
          onTextSearch={handleTextSearch}
          onImageSearch={handleImageSearch}
          loading={loading}
        />
        
        <FilterPanel
          filters={filters}
          onFiltersChange={setFilters}
          filterOptions={filterOptions}
        />
        
        <ResultsGrid results={results} loading={loading} />
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h3 className="text-lg font-semibold mb-2">
              Vector Database Operations Demonstrated
            </h3>
            <div className="flex justify-center space-x-8 text-sm">
              <span>✅ Upsert Operations</span>
              <span>✅ Query with Similarity</span>
              <span>✅ Advanced Filtering</span>
              <span>✅ Batch Operations</span>
            </div>
            <p className="text-gray-400 mt-4">
              Fashion Product Recommendation System 
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
