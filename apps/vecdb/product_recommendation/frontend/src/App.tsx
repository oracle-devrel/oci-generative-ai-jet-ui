import React, { useState, useEffect, useMemo } from 'react';
import { SearchBar } from './components/SearchBar';
import { FilterSidebar } from './components/FilterSidebar';
import { ProductGrid } from './components/ProductGrid';
import { ProductManager } from './components/ProductManager';
import { RecommendationCarousel } from './components/RecommendationCarousel';
import { getPriceRange, Product } from './data/sampleProducts';
import axios from 'axios';
import { RecommendedProduct } from './data/userProfile';

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000';

function App() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [activeTab] = useState<'search' | 'manage'>('search');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [displayProducts, setDisplayProducts] = useState<Product[]>([]);
  const [imageSearchFile, setImageSearchFile] = useState<File | null>(null);
  const [searchMode, setSearchMode] = useState<'text' | 'image'>('text');
  const [availableCategories, setAvailableCategories] = useState<string[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const fullPriceRange = getPriceRange();

  const [searchQuery, setSearchQuery] = useState('');
  const [priceRange, setPriceRange] = useState({ min: 0, max: 1000 });
  const [priceRangeDraft, setPriceRangeDraft] = useState({ min: '0', max: '1000' });
  const [topK, setTopK] = useState(20);

  useEffect(() => {
    const minString = priceRange.min.toString();
    const maxString = priceRange.max.toString();
    setPriceRangeDraft((prev) =>
      prev.min === minString && prev.max === maxString
        ? prev
        : { min: minString, max: maxString }
    );
  }, [priceRange.min, priceRange.max]);

  const categoryQueryParam = useMemo(
    () => (selectedCategories.length > 0 ? selectedCategories.join(',') : undefined),
    [selectedCategories]
  );

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await axios.get<string[]>(`${API_BASE_URL}/categories`);
        setAvailableCategories(response.data);
      } catch (error) {
        console.error('Failed to load categories', error);
      }
    };

    void fetchCategories();
  }, []);

  useEffect(() => {
    if (imageSearchFile) {
      void handleImageSearch(imageSearchFile);
    } else {
      void handleTextSearch(searchQuery);
    }
  }, [priceRange, topK, categoryQueryParam]);

  const handlePriceDraftChange = (field: 'min' | 'max', value: string) => {
    if (!/^\d*(?:\.\d{0,2})?$/.test(value)) {
      return;
    }
    setPriceRangeDraft((prev) => ({ ...prev, [field]: value }));
  };

  const commitPriceDraft = (field: 'min' | 'max') => {
    const rawMin = priceRangeDraft.min.trim();
    const rawMax = priceRangeDraft.max.trim();

    let parsedMin = rawMin === '' ? priceRange.min : Number(rawMin);
    let parsedMax = rawMax === '' ? priceRange.max : Number(rawMax);

    if (!Number.isFinite(parsedMin)) {
      parsedMin = priceRange.min;
    }
    if (!Number.isFinite(parsedMax)) {
      parsedMax = priceRange.max;
    }

    parsedMin = Math.max(fullPriceRange.min, Math.min(parsedMin, fullPriceRange.max));
    parsedMax = Math.max(fullPriceRange.min, Math.min(parsedMax, fullPriceRange.max));

    if (parsedMin > parsedMax) {
      if (field === 'min') {
        parsedMax = parsedMin;
      } else {
        parsedMin = parsedMax;
      }
    }

    setPriceRange({ min: parsedMin, max: parsedMax });
  };

  const resetPriceRange = () => {
    const reset = { min: fullPriceRange.min, max: fullPriceRange.max };
    setPriceRange(reset);
    setPriceRangeDraft({ min: reset.min.toString(), max: reset.max.toString() });
  };

  function formatCategory(rawCategory: string): string {
    return rawCategory
      .split('|')
      .map((part) => part.trim())
      .join(', ');
  }

  const handleProductSelect = async (product: Product | RecommendedProduct) => {
    const selected: Product = {
      ...product,
      id: product.id,
      category: formatCategory(product.category),
      title: product.title,
      description: product.description,
      image: product.image,
      price: product.price,
    };

    setSelectedProduct(selected);

    const payload = {
      title: selected.title,
      description: selected.description,
      image: selected.image,
      price: selected.price,
      category: selected.category,
      top_k: 20,
      min_price: 0,
      max_price: 10000,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/vector-search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      setDisplayProducts(data);
    } catch (error) {
      console.error('Error performing vector search:', error);
    }
  };

  const handleTextSearch = async (query: string) => {
    setSearchQuery(query);
    setImageSearchFile(null);
    setIsLoading(true);
    setSelectedProduct(null);

    try {
      if (query.trim()) {
        const response = await axios.get(`${API_BASE_URL}/search`, {
          params: {
            query,
            top_k: topK,
            min_price: priceRange.min,
            max_price: priceRange.max,
            categories: categoryQueryParam,
          },
        });
        setDisplayProducts(response.data);
      } else {
        const response = await axios.get(`${API_BASE_URL}/products`, {
          params: {
            top_k: topK,
            min_price: priceRange.min,
            max_price: priceRange.max,
            categories: categoryQueryParam,
          },
        });
        setDisplayProducts(response.data);
      }
    } catch (error) {
      console.error('Text search failed:', error);
      setDisplayProducts([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageSearch = async (file: File) => {
    setImageSearchFile(file);
    setSearchQuery(`Image search: ${file.name}`);
    setIsLoading(true);
    setSelectedProduct(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('top_k', String(topK));
      formData.append('min_price', String(priceRange.min));
      formData.append('max_price', String(priceRange.max));
      if (categoryQueryParam) {
        formData.append('categories', categoryQueryParam);
      }

      const response = await axios.post(`${API_BASE_URL}/image-search`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setDisplayProducts(response.data);
    } catch (error) {
      console.error('Image search failed:', error);
      setDisplayProducts([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCategoryToggle = (category: string) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((item) => item !== category)
        : [...prev, category]
    );
  };

  const handleClearCategories = () => {
    setSelectedCategories([]);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">VS</span>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Visual Search</h1>
                <div className="text-xs text-gray-500 mt-1">Powered by Oracle AI Database</div>
              </div>
            </div>
            <div className="text-sm text-gray-600">
              {displayProducts.length} products found
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {activeTab === 'search' ? (
          <>
            <SearchBar
              onTextSearch={handleTextSearch}
              onImageSearch={handleImageSearch}
              searchQuery={searchQuery}
              searchMode={searchMode}
              onSearchModeChange={setSearchMode}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />

            <div className="flex gap-6">
              {isFilterOpen && (
                <aside className="w-64">
                  <FilterSidebar
                    priceRange={fullPriceRange}
                    selectedPriceRange={priceRange}
                    priceDraft={priceRangeDraft}
                    onPriceDraftChange={handlePriceDraftChange}
                    onPriceDraftCommit={commitPriceDraft}
                    onPriceRangeReset={resetPriceRange}
                    topK={topK}
                    onTopKChange={setTopK}
                    categories={availableCategories}
                    selectedCategories={selectedCategories}
                    onCategoryToggle={handleCategoryToggle}
                    onClearCategories={handleClearCategories}
                    isOpen={true}
                    onToggle={() => setIsFilterOpen(false)}
                  />
                </aside>
              )}

              <main className="flex-1">
                {!selectedProduct && (
                  <RecommendationCarousel onProductSelect={handleProductSelect} />
                )}
                {selectedProduct && (
                  <div className="mt-6 mb-6 p-6 bg-white border rounded-lg flex items-start gap-6">
                    <div className="flex-1">
                      <h2 className="text-xl font-semibold mb-2">Selected Product</h2>
                      <p className="mb-1"><strong>Title:</strong> {selectedProduct.title}</p>
                      <p className="mb-1"><strong>Description:</strong> {selectedProduct.description}</p>
                      <p className="mb-1"><strong>Price:</strong> ${selectedProduct.price}</p>
                      <p className="mb-1"><strong>Category:</strong> {selectedProduct.category}</p>
                    </div>

                    {selectedProduct.image && (
                      <div className="w-48 h-48 flex-shrink-0">
                        <img
                          src={selectedProduct.image}
                          alt={selectedProduct.title}
                          className="w-full h-full object-contain rounded border"
                        />
                      </div>
                    )}
                  </div>
                )}
                <ProductGrid
                  products={displayProducts}
                  viewMode={viewMode}
                  onProductSelect={handleProductSelect}
                />
              </main>
            </div>
          </>
        ) : (
          <ProductManager
            products={displayProducts}
            onProductsChange={setDisplayProducts}
          />
        )}
      </div>
    </div>
  );
}

export default App;
