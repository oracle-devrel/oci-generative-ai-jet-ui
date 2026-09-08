import React from 'react';
import { Filter } from 'lucide-react';

interface FilterSidebarProps {
  priceRange: { min: number; max: number };
  selectedPriceRange: { min: number; max: number };
  priceDraft: { min: string; max: string };
  onPriceDraftChange: (field: 'min' | 'max', value: string) => void;
  onPriceDraftCommit: (field: 'min' | 'max') => void;
  onPriceRangeReset: () => void;
  topK: number;
  onTopKChange: (k: number) => void;
  categories: string[];
  selectedCategories: string[];
  onCategoryToggle: (category: string) => void;
  onClearCategories: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const FilterSidebar: React.FC<FilterSidebarProps> = ({
  priceRange,
  selectedPriceRange,
  priceDraft,
  onPriceDraftChange,
  onPriceDraftCommit,
  onPriceRangeReset,
  topK,
  onTopKChange,
  categories,
  selectedCategories,
  onCategoryToggle,
  onClearCategories,
  isOpen,
  onToggle
}) => {
  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="p-4 border-b border-gray-200 flex items-center gap-2">
        <Filter className="w-4 h-4 text-gray-600" />
        <h3 className="font-medium text-gray-900">Filters</h3>
      </div>
      
      <div className="p-4 space-y-6">
        {/* Results Count */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Show Results
          </label>
          <select
            value={topK}
            onChange={(e) => onTopKChange(Number(e.target.value))}
            className="w-full p-2 border border-gray-200 rounded-md focus:ring-2 focus:ring-blue-500 text-sm"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={30}>30</option>
            <option value={40}>40</option>
            <option value={50}>50</option>
          </select>
        </div>

        {/* Price Range */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Min Price</label>
            <input
              type="number"
              min={priceRange.min}
              max={selectedPriceRange.max}
              step="0.01"
              value={priceDraft.min}
              onChange={(e) => onPriceDraftChange('min', e.target.value)}
              onBlur={() => onPriceDraftCommit('min')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.currentTarget.blur();
                }
              }}
              className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Max Price</label>
            <input
              type="number"
              min={selectedPriceRange.min}
              max={priceRange.max}
              step="0.01"
              value={priceDraft.max}
              onChange={(e) => onPriceDraftChange('max', e.target.value)}
              onBlur={() => onPriceDraftCommit('max')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.currentTarget.blur();
                }
              }}
              className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Categories */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Categories</label>
            <button
              type="button"
              onClick={onClearCategories}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              Clear
            </button>
          </div>
          <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
            {categories.length === 0 ? (
              <p className="text-xs text-gray-500">No categories available.</p>
            ) : (
              categories.map((category) => {
                const isSelected = selectedCategories.includes(category);
                return (
                  <label
                    key={category}
                    className="flex items-center gap-2 text-sm text-gray-700"
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onCategoryToggle(category)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="flex-1 truncate" title={category}>
                      {category}
                    </span>
                  </label>
                );
              })
            )}
          </div>
        </div>

        {/* Clear Filters */}
        <div className="flex flex-col gap-2">
          <button
            onClick={() => {
              onPriceRangeReset();
              onTopKChange(20);
              onClearCategories();
            }}
            className="w-full py-2 px-6 text-sm text-gray-600 hover:text-gray-900 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap text-center"
          >
            Clear All
          </button>
        </div>
      </div>
    </div>
  );
};
