import React, { useState, useRef } from 'react';
import { Search, Upload, Image, Settings } from 'lucide-react';

interface SearchInterfaceProps {
  onTextSearch: (query: string, topK: number) => void;
  onImageSearch: (file: File, topK: number) => void;
  loading: boolean;
}

const SearchInterface: React.FC<SearchInterfaceProps> = ({
  onTextSearch,
  onImageSearch,
  loading,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [uploadedImage, setUploadedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleTextSearch = () => {
    if (searchQuery.trim()) {
      onTextSearch(searchQuery.trim(), topK);
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleImageSearch = () => {
    if (uploadedImage) {
      onImageSearch(uploadedImage, topK);
    }
  };

  const clearImage = () => {
    setUploadedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          Fashion Product Finder
        </h1>
        <p className="text-gray-600 text-lg">
          Search by text description or upload an image to find similar products
        </p>
        <div className="mt-2 text-sm text-gray-500">
          Powered by Oracle AI Database
        </div>
      </div>

      {/* Top-K Configuration */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-4">
          <Settings className="text-gray-600" size={20} />
          <label className="text-sm font-medium text-gray-700">
            Number of recommendations:
          </label>
          <input
            type="number"
            min="1"
            max="20"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
            className="w-20 px-3 py-1 border border-gray-300 rounded-md text-center focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Text Search */}
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Search className="text-blue-600" size={24} />
            Search by Description
          </h3>
          
          <div className="relative">
            <input
              type="text"
              placeholder="e.g., mens green polo tshirt"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleTextSearch()}
              className="w-full px-4 py-3 pl-12 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
            />
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
          </div>
          
          <button
            onClick={handleTextSearch}
            disabled={!searchQuery.trim() || loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-lg font-medium hover:from-blue-700 hover:to-blue-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Searching...' : 'Search Products'}
          </button>
        </div>

        {/* Image Search */}
        <div className="space-y-4">
          <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            <Image className="text-green-600" size={24} />
            Search by Image
          </h3>
          
          <div className="relative">
            <input
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              ref={fileInputRef}
              className="hidden"
            />
            
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-gray-400 transition-colors duration-200"
            >
              <div className="flex flex-col items-center space-y-2">
                <Upload className="text-gray-400" size={32} />
                <span className="text-gray-600">Click to upload image</span>
                <span className="text-sm text-gray-500">PNG, JPG up to 10MB</span>
              </div>
            </button>
          </div>

          {imagePreview && (
            <div className="relative">
              <img
                src={imagePreview}
                alt="Upload preview"
                className="w-full h-40 object-cover rounded-lg"
              />
              <button
                onClick={clearImage}
                className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-red-600 transition-colors"
              >
                ×
              </button>
            </div>
          )}
          
          <button
            onClick={handleImageSearch}
            disabled={!uploadedImage || loading}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 text-white px-6 py-3 rounded-lg font-medium hover:from-green-700 hover:to-green-800 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Processing...' : 'Find Similar Products'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SearchInterface;
