import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Gift } from 'lucide-react';
import axios from 'axios';

interface RecommendedProduct {
  id: string;
  category: string;
  description: string;
  image: string;
  price: number;
  specification: string;
  text: string;
  title: string;
}

interface PriceRange {
  min: number;
  max: number;
}

interface RecommendationCarouselProps {
  topK?: number;
  priceRange?: PriceRange;
  selectedCategories?: string[];
  onProductSelect?: (product: RecommendedProduct) => void;
}

const API_BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://127.0.0.1:8000';

export const RecommendationCarousel: React.FC<RecommendationCarouselProps> = ({
  topK,
  priceRange,
  selectedCategories,
  onProductSelect,
}) => {
  const [recommendations, setRecommendations] = useState<RecommendedProduct[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const itemsPerView = 6;

  const normalizeProducts = (data: RecommendedProduct[]): RecommendedProduct[] => {
    return data.map((item, index) => ({
      id: item.id || `fallback-id-${index}`,
      category: item.category || '',
      description: item.description || '',
      image: item.image || '',
      price: Number(item.price) || 0,
      specification: item.specification || '',
      text: item.text || '',
      title: item.title || '',
    }));
  };

  const getRecommendedProducts = async (): Promise<RecommendedProduct[]> => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, unknown> = {};
      if (topK) params.top_k = topK;
      if (priceRange) {
        params.min_price = priceRange.min;
        params.max_price = priceRange.max;
      }
      if (selectedCategories && selectedCategories.length > 0) {
        params.categories = selectedCategories.join(',');
      }

      const response = await axios.get<RecommendedProduct[]>(`${API_BASE_URL}/vector-search/history`, {
        params,
      });

      return normalizeProducts(response.data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch recommended products.');
      return [];
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      const products = await getRecommendedProducts();
      setRecommendations(products);
    };

    void fetchData();
  }, [topK, priceRange, selectedCategories]);

  const nextSlide = () => {
    setCurrentIndex((prev) =>
      prev + itemsPerView >= recommendations.length ? 0 : prev + itemsPerView
    );
  };

  const prevSlide = () => {
    setCurrentIndex((prev) =>
      prev === 0 ? Math.max(0, recommendations.length - itemsPerView) : Math.max(0, prev - itemsPerView)
    );
  };

  const visibleItems = recommendations.slice(currentIndex, currentIndex + itemsPerView);

  if (loading) return <div>Loading recommended products...</div>;
  if (error) return <div className="text-red-600">Error: {error}</div>;
  if (recommendations.length === 0) return <div>No recommended products found.</div>;

  return (
    <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg p-6 mb-8 border border-amber-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-amber-500 rounded-full flex items-center justify-center">
            <Gift className="w-4 h-4 text-white" />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">Previous search</h2>
        </div>
      </div>

      <div className="relative">
        <div className="flex gap-4 overflow-hidden">
          {visibleItems.map((item) => (
            <div
              key={item.id}
              className="flex-shrink-0 w-40 cursor-pointer group"
              onClick={() => onProductSelect?.(item)}
            >
              <div className="aspect-square rounded-lg overflow-hidden mb-2 group-hover:shadow-md transition-shadow">
                <img
                  src={item.image}
                  alt={item.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                />
              </div>
              <h3 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">{item.title}</h3>
              <p className="text-lg font-semibold text-gray-900">${item.price.toFixed(2)}</p>
            </div>
          ))}
        </div>

        {recommendations.length > itemsPerView && (
          <>
            <button
              onClick={prevSlide}
              className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-4 w-10 h-10 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-50 transition-colors z-10"
              disabled={currentIndex === 0}
            >
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </button>
            <button
              onClick={nextSlide}
              className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-4 w-10 h-10 bg-white rounded-full shadow-lg flex items-center justify-center hover:bg-gray-50 transition-colors z-10"
            >
              <ChevronRight className="w-5 h-5 text-gray-600" />
            </button>
          </>
        )}
      </div>
    </div>
  );
};
