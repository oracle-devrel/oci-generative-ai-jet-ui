import React from 'react';
import { SearchResult } from '../types/product';
import ProductCard from './ProductCard';

interface ResultsGridProps {
  results: SearchResult[];
  loading: boolean;
}

const ResultsGrid: React.FC<ResultsGridProps> = ({ results, loading }) => {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-12">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="text-gray-600">Searching for similar products...</p>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-12">
        <div className="text-center">
          <p className="text-gray-600 text-lg">
            No products found. Try adjusting your search query or filters.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-2xl font-semibold text-gray-800 mb-2">
          Search Results
        </h2>
        <p className="text-gray-600">
          Found {results.length} similar products, ranked by similarity score
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {results.map((product, index) => (
          <ProductCard
            key={product.id}
            product={product}
            rank={index + 1}
          />
        ))}
      </div>
    </div>
  );
};

export default ResultsGrid;