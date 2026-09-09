import React, { useState } from 'react';
import { Plus, Trash2, Database, Upload } from 'lucide-react';
import { Product } from '../data/sampleProducts';

interface ProductManagerProps {
  products: Product[];
  onProductsChange: (products: Product[]) => void;
}

export const ProductManager: React.FC<ProductManagerProps> = ({ products, onProductsChange }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [activeTab, setActiveTab] = useState<'manual' | 'csv'>('manual');

  const [newProduct, setNewProduct] = useState({
    title: '',
    description: '',
    price: '',
    category: '',
    image: '',
    specification: '',
    text: ''
  });

  const handleAddProduct = (e: React.FormEvent) => {
    e.preventDefault();

    const product: Product = {
      id: `prod-${Date.now()}`,
      title: newProduct.title,
      description: newProduct.description,
      price: parseFloat(newProduct.price),
      category: newProduct.category,
      image: newProduct.image || 'https://images.pexels.com/photos/163100/circuit-circuit-board-resistor-computer-163100.jpeg?auto=compress&cs=tinysrgb&w=500',
      specification: newProduct.specification,
      text: newProduct.text || newProduct.description
    };

    onProductsChange([...products, product]);
    setNewProduct({
      title: '',
      description: '',
      price: '',
      category: '',
      image: '',
      specification: '',
      text: ''
    });
    setShowAddForm(false);
  };

  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split('\n').filter(Boolean);
      const newProducts: Product[] = lines.slice(1).map((line, i) => {
        const [title, description, price, category, image] = line.split(',').map((s) => s.trim());
        return {
          id: `csv-prod-${Date.now()}-${i}`,
          title,
          description,
          price: parseFloat(price),
          category,
          image: image || 'https://images.pexels.com/photos/163100/circuit-circuit-board-resistor-computer-163100.jpeg?auto=compress&cs=tinysrgb&w=500',
          specification: '',
          text: description
        };
      });

      onProductsChange([...products, ...newProducts]);
      setShowAddForm(false);
    };

    reader.readAsText(file);
  };

  const handleDeleteProduct = (productId: string) => {
    onProductsChange(products.filter(p => p.id !== productId));
  };

  const createIndex = () => {
    alert('Creating index with embeddings for all products...');
  };

  const renderModal = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-xl">
        <h3 className="text-lg font-semibold mb-4">Add New Product</h3>

        {/* Tabs */}
        <div className="flex border-b mb-4">
          <button
            onClick={() => setActiveTab('manual')}
            className={`flex-1 py-2 text-center font-medium ${
              activeTab === 'manual' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
            }`}
          >
            Manual Entry
          </button>
          <button
            onClick={() => setActiveTab('csv')}
            className={`flex-1 py-2 text-center font-medium ${
              activeTab === 'csv' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'
            }`}
          >
            CSV Upload
          </button>
        </div>

        {activeTab === 'manual' ? (
          <form onSubmit={handleAddProduct} className="space-y-4">
            <input
              type="text"
              placeholder="Product Title"
              value={newProduct.title}
              onChange={(e) => setNewProduct({ ...newProduct, title: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg"
              required
            />
            <textarea
              placeholder="Description"
              value={newProduct.description}
              onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg h-20"
              required
            />
            <input
              type="number"
              step="0.01"
              placeholder="Price"
              value={newProduct.price}
              onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg"
              required
            />
            <input
              type="text"
              placeholder="Category"
              value={newProduct.category}
              onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg"
              required
            />
            <input
              type="url"
              placeholder="Image URL (optional)"
              value={newProduct.image}
              onChange={(e) => setNewProduct({ ...newProduct, image: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg"
            />
            <div className="flex gap-3">
              <button
                type="submit"
                className="flex-1 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Add Product
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <input
              type="file"
              accept=".csv"
              onChange={handleCSVUpload}
              className="w-full p-3 border border-gray-300 rounded-lg"
            />
            <p className="text-sm text-gray-500">
              Ensure your CSV includes headers: <code>title, description, price, category, image</code>
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="flex-1 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Product Management</h2>
          <p className="text-gray-600">Manage your product catalog and embeddings</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={createIndex}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <Database className="w-4 h-4" />
            Create Index with Embedding
          </button>
          <button
            onClick={() => {
              setActiveTab('manual');
              setShowAddForm(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Product
          </button>
        </div>
      </div>

      {/* Product List */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-medium text-gray-900">Products ({products.length})</h3>
        </div>
        <div className="divide-y divide-gray-200">
          {products.map((product) => (
            <div key={product.id} className="p-4 flex items-center gap-4">
              <img
                src={product.image}
                alt={product.title}
                className="w-16 h-16 object-cover rounded-lg"
              />
              <div className="flex-1">
                <h4 className="font-medium text-gray-900">{product.title}</h4>
                <p className="text-sm text-gray-600 line-clamp-1">{product.description}</p>
                <div className="text-lg font-semibold text-gray-900">${product.price}</div>
              </div>
              <button
                onClick={() => handleDeleteProduct(product.id)}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Modal */}
      {showAddForm && renderModal()}
    </div>
  );
};
