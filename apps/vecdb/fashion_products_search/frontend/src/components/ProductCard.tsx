import React from 'react';
import { SearchResult } from '../types/product';

interface ProductCardProps {
  product: SearchResult;
  rank: number;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, rank }) => {
  const {
    imageUrl,
    productDisplayName,
    similarityScore,
    gender,
    masterCategory,
    articleType,
    baseColour,
    season,
    year,
    usage,
    subCategory,
  } = product;

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
      <div className="relative">
        <img
          src={imageUrl}
          alt={productDisplayName}
          className="w-full h-64 object-cover"
        />
        <div className="absolute top-4 left-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white px-3 py-1 rounded-full text-sm font-medium">
          #{rank}
        </div>
        <div className="absolute top-4 right-4 bg-black bg-opacity-70 text-white px-3 py-1 rounded-full text-sm">
          {(similarityScore * 100).toFixed(1)}% match
        </div>
      </div>
      
      <div className="p-6">
        <h3 className="text-xl font-semibold text-gray-800 mb-3">
          {productDisplayName}
        </h3>
        
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Gender:</span>
              <span className="font-medium">{gender}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Category:</span>
              <span className="font-medium">{masterCategory}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Type:</span>
              <span className="font-medium">{articleType}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Color:</span>
              <span className="font-medium">{baseColour}</span>
            </div>
          </div>
          
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Season:</span>
              <span className="font-medium">{season}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Year:</span>
              <span className="font-medium">{year ?? '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Usage:</span>
              <span className="font-medium">{usage}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Sub-cat:</span>
              <span className="font-medium">{subCategory}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
