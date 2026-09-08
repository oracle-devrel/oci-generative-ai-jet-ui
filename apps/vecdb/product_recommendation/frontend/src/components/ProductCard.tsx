import React from 'react';
import { Product } from '../data/sampleProducts';

interface ProductCardProps {
  product: Product;
  viewMode: 'grid' | 'list';
  onSelect?: (product: Product) => void; // <-- added
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, viewMode, onSelect }) => {
  const handleClick = () => {
    if (onSelect) onSelect(product);
  };

  if (viewMode === 'list') {
    return (
      <div
        onClick={handleClick}
        className="cursor-pointer bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow"
      >
        <div className="flex">
          <div className="w-48 h-32 flex-shrink-0">
            <img
              src={product.image}
              alt={product.title}
              className="w-full h-full object-cover rounded-l-lg"
            />
          </div>
          <div className="flex-1 p-4">
            <h3 className="font-medium text-gray-900 mb-2 line-clamp-2">
              {product.title}
            </h3>
            <p className="text-sm text-gray-600 mb-2 line-clamp-2">
              {product.description}
            </p>
            <div className="text-lg font-semibold text-gray-900">
              ${product.price}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className="cursor-pointer bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow overflow-hidden"
    >
      <div className="aspect-square">
        <img
          src={product.image}
          alt={product.title}
          className="w-full h-full object-cover"
        />
      </div>
      <div className="p-4">
        <h3 className="font-medium text-gray-900 mb-2 line-clamp-2 text-sm">
          {product.title}
        </h3>
        <p className="text-xs text-gray-600 mb-2 line-clamp-2">
          {product.description}
        </p>
        <div className="text-lg font-semibold text-gray-900">
          ${product.price}
        </div>
      </div>
    </div>
  );
};
