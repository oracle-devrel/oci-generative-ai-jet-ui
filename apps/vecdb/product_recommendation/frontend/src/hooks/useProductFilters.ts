import { useState, useMemo } from 'react';
import { Product } from '../data/sampleProducts';

export const useProductFilters = (products: Product[]) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [priceRange, setPriceRange] = useState({ min: 0, max: 1000 });
  const [topK, setTopK] = useState(20);

  const filteredProducts = useMemo(() => {
    let filtered = products;

    // Text search
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(product =>
        product.title.toLowerCase().includes(query) ||
        product.description.toLowerCase().includes(query) ||
        product.text.toLowerCase().includes(query) ||
        product.category.toLowerCase().includes(query)
      );
    }

    // Category filter
    if (selectedCategories.length > 0) {
      filtered = filtered.filter(product =>
        selectedCategories.some(category =>
          product.category.toLowerCase().includes(category.toLowerCase())
        )
      );
    }

    // Price range filter
    filtered = filtered.filter(product =>
      product.price >= priceRange.min && product.price <= priceRange.max
    );

    // Sort by relevance (price for now, could be enhanced with actual search relevance)
    filtered.sort((a, b) => {
      if (searchQuery.trim()) {
        // If searching, prioritize title matches
        const aTitle = a.title.toLowerCase().includes(searchQuery.toLowerCase());
        const bTitle = b.title.toLowerCase().includes(searchQuery.toLowerCase());
        if (aTitle && !bTitle) return -1;
        if (!aTitle && bTitle) return 1;
      }
      return a.price - b.price;
    });

    // Limit to top K results
    return filtered.slice(0, topK);
  }, [products, searchQuery, selectedCategories, priceRange, topK]);

  return {
    searchQuery,
    setSearchQuery,
    selectedCategories,
    setSelectedCategories,
    priceRange,
    setPriceRange,
    topK,
    setTopK,
    filteredProducts
  };
};