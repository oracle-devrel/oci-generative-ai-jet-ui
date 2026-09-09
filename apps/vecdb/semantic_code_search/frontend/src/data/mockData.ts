import { FileNode, CodeEmbedding } from '../types';

export const mockFileTree: FileNode = {
  id: 'root',
  name: 'searchable-codebase',
  type: 'folder',
  path: '/',
  children: [
    {
      id: 'src',
      name: 'src',
      type: 'folder',
      path: '/src',
      children: [
        {
          id: 'components',
          name: 'components',
          type: 'folder',
          path: '/src/components',
          children: [
            {
              id: 'header',
              name: 'Header.tsx',
              type: 'file',
              path: '/src/components/Header.tsx',
              language: 'typescript',
              content: `// Header component with search functionality
import React from 'react';
import { Search, Menu } from 'lucide-react';

interface HeaderProps {
  onMenuToggle: () => void;
  onSearch: (query: string) => void;
}

// Main header component that handles navigation and search
export const Header: React.FC<HeaderProps> = ({ onMenuToggle, onSearch }) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);
    const query = formData.get('search') as string;
    onSearch(query);
  };

  // Render header with search bar and menu toggle
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <button onClick={onMenuToggle} className="lg:hidden">
            <Menu className="w-6 h-6" />
          </button>
          <h1 className="text-xl font-semibold text-gray-900">My App</h1>
        </div>
        <form onSubmit={handleSubmit} className="flex-1 max-w-xl mx-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              name="search"
              type="text"
              placeholder="Search anything..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </form>
      </div>
    </header>
  );
};`
            },
            {
              id: 'userprofile',
              name: 'UserProfile.tsx',
              type: 'file',
              path: '/src/components/UserProfile.tsx',
              language: 'typescript',
              content: `// User profile component with data fetching
import React, { useState, useEffect } from 'react';
import { User, Mail, Phone, MapPin } from 'lucide-react';

interface UserData {
  id: string;
  name: string;
  email: string;
  phone: string;
  location: string;
  avatar?: string;
}

// Component that displays user profile information
export const UserProfile: React.FC = () => {
  const [user, setUser] = useState<UserData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUserData();
  }, []);

  // Async function to fetch user data from API
  const fetchUserData = async () => {
    try {
      setLoading(true);
      const userData = await mockApiCall();
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Mock API call that simulates server response
  const mockApiCall = (): Promise<UserData> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          id: '123',
          name: 'John Doe',
          email: 'john@example.com',
          phone: '+1 234 567 8900',
          location: 'San Francisco, CA'
        });
      }, 1000);
    });
  };

  if (loading) {
    return <div className="animate-pulse bg-gray-200 h-48 rounded-lg"></div>;
  }

  if (!user) {
    return <div className="text-red-500">Failed to load user data</div>;
  }

  // Render user profile with contact information
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center gap-4 mb-6">
        <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center">
          <User className="w-8 h-8 text-white" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{user.name}</h2>
          <p className="text-gray-600">User ID: {user.id}</p>
        </div>
      </div>
      
      <div className="space-y-3">
        <div className="flex items-center gap-3 text-gray-700">
          <Mail className="w-5 h-5" />
          <span>{user.email}</span>
        </div>
        <div className="flex items-center gap-3 text-gray-700">
          <Phone className="w-5 h-5" />
          <span>{user.phone}</span>
        </div>
        <div className="flex items-center gap-3 text-gray-700">
          <MapPin className="w-5 h-5" />
          <span>{user.location}</span>
        </div>
      </div>
    </div>
  );
};`
            },
            {
              id: 'productlist',
              name: 'ProductList.tsx',
              type: 'file',
              path: '/src/components/ProductList.tsx',
              language: 'typescript',
              content: `// Product listing component with filtering and sorting
import React, { useState, useMemo } from 'react';
import { ShoppingCart, Star, Filter } from 'lucide-react';

interface Product {
  id: string;
  name: string;
  price: number;
  rating: number;
  category: string;
  inStock: boolean;
  description: string;
}

// Component that displays a list of products with filtering
export const ProductList: React.FC = () => {
  const [products] = useState<Product[]>([
    {
      id: '1',
      name: 'Wireless Headphones',
      price: 99.99,
      rating: 4.5,
      category: 'Electronics',
      inStock: true,
      description: 'High-quality wireless headphones with noise cancellation'
    },
    {
      id: '2',
      name: 'Coffee Maker',
      price: 149.99,
      rating: 4.2,
      category: 'Appliances',
      inStock: false,
      description: 'Automatic drip coffee maker with programmable timer'
    }
  ]);
  
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');

  // Filter and sort products based on user selection
  const filteredProducts = useMemo(() => {
    let filtered = products;
    
    if (filter !== 'all') {
      filtered = products.filter(product => 
        filter === 'inStock' ? product.inStock : product.category.toLowerCase() === filter
      );
    }
    
    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'price':
          return a.price - b.price;
        case 'rating':
          return b.rating - a.rating;
        default:
          return a.name.localeCompare(b.name);
      }
    });
  }, [products, filter, sortBy]);

  // Handle adding product to cart
  const handleAddToCart = (productId: string) => {
    console.log('Adding product to cart:', productId);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Products</h2>
        <div className="flex gap-4">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="all">All Categories</option>
            <option value="electronics">Electronics</option>
            <option value="appliances">Appliances</option>
            <option value="inStock">In Stock Only</option>
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="name">Sort by Name</option>
            <option value="price">Sort by Price</option>
            <option value="rating">Sort by Rating</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProducts.map((product) => (
          <div key={product.id} className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">{product.name}</h3>
            <p className="text-gray-600 text-sm mb-4">{product.description}</p>
            
            <div className="flex items-center justify-between mb-4">
              <span className="text-2xl font-bold text-blue-600">\${product.price}</span>
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-400 fill-current" />
                <span className="text-sm text-gray-600">{product.rating}</span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className={\`text-sm px-2 py-1 rounded \${product.inStock ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}\`}>
                {product.inStock ? 'In Stock' : 'Out of Stock'}
              </span>
              <button
                onClick={() => handleAddToCart(product.id)}
                disabled={!product.inStock}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                <ShoppingCart className="w-4 h-4" />
                Add to Cart
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};`
            }
          ]
        },
        {
          id: 'utils',
          name: 'utils',
          type: 'folder',
          path: '/src/utils',
          children: [
            {
              id: 'api',
              name: 'api.ts',
              type: 'file',
              path: '/src/utils/api.ts',
              language: 'typescript',
              content: `// API client utilities for making HTTP requests
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

// Custom error class for API-related errors
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// HTTP client with common REST methods
export const apiClient = {
  // GET request method
  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(\`\${API_BASE_URL}\${endpoint}\`);
    if (!response.ok) {
      throw new ApiError(response.status, \`GET \${endpoint} failed\`);
    }
    return response.json();
  },

  // POST request method for creating resources
  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(\`\${API_BASE_URL}\${endpoint}\`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new ApiError(response.status, \`POST \${endpoint} failed\`);
    }
    return response.json();
  },

  // PUT request method for updating resources
  async put<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(\`\${API_BASE_URL}\${endpoint}\`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new ApiError(response.status, \`PUT \${endpoint} failed\`);
    }
    return response.json();
  },

  // DELETE request method for removing resources
  async delete<T>(endpoint: string): Promise<T> {
    const response = await fetch(\`\${API_BASE_URL}\${endpoint}\`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new ApiError(response.status, \`DELETE \${endpoint} failed\`);
    }
    return response.json();
  }
};`
            },
            {
              id: 'validation',
              name: 'validation.ts',
              type: 'file',
              path: '/src/utils/validation.ts',
              language: 'typescript',
              content: `// Form validation utilities

// Email validation using regex pattern
export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

// Phone number validation with international format support
export const validatePhone = (phone: string): boolean => {
  const phoneRegex = /^\+?[\d\s-()]{10,}$/;
  return phoneRegex.test(phone);
};

// Check if required field is not empty
export const validateRequired = (value: string): boolean => {
  return value.trim().length > 0;
};

// Validate minimum string length
export const validateMinLength = (value: string, minLength: number): boolean => {
  return value.length >= minLength;
};

// Validate maximum string length
export const validateMaxLength = (value: string, maxLength: number): boolean => {
  return value.length <= maxLength;
};

// Interface for validation rules
export interface ValidationRule {
  field: string;
  validator: (value: any) => boolean;
  message: string;
}

// Validate entire form against multiple rules
export const validateForm = (data: Record<string, any>, rules: ValidationRule[]): string[] => {
  const errors: string[] = [];
  
  for (const rule of rules) {
    const value = data[rule.field];
    if (!rule.validator(value)) {
      errors.push(rule.message);
    }
  }
  
  return errors;
};`
            },
            {
              id: 'helpers',
              name: 'helpers.ts',
              type: 'file',
              path: '/src/utils/helpers.ts',
              language: 'typescript',
              content: `// General utility helper functions

// Format currency values for display
export const formatCurrency = (amount: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
  }).format(amount);
};

// Format date for user-friendly display
export const formatDate = (date: Date | string): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

// Debounce function to limit API calls
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(null, args), wait);
  };
};

// Generate random ID for temporary use
export const generateId = (): string => {
  return Math.random().toString(36).substr(2, 9);
};

// Capitalize first letter of string
export const capitalize = (str: string): string => {
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// Deep clone object utility
export const deepClone = <T>(obj: T): T => {
  return JSON.parse(JSON.stringify(obj));
};`
            }
          ]
        },
        {
          id: 'hooks',
          name: 'hooks',
          type: 'folder',
          path: '/src/hooks',
          children: [
            {
              id: 'useLocalStorage',
              name: 'useLocalStorage.ts',
              type: 'file',
              path: '/src/hooks/useLocalStorage.ts',
              language: 'typescript',
              content: `// Custom hook for localStorage management
import { useState, useEffect } from 'react';

// Hook that syncs state with localStorage
export const useLocalStorage = <T>(key: string, initialValue: T) => {
  // Get value from localStorage or use initial value
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error('Error reading from localStorage:', error);
      return initialValue;
    }
  });

  // Function to update both state and localStorage
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error('Error writing to localStorage:', error);
    }
  };

  return [storedValue, setValue] as const;
};`
            },
            {
              id: 'useApi',
              name: 'useApi.ts',
              type: 'file',
              path: '/src/hooks/useApi.ts',
              language: 'typescript',
              content: `// Custom hook for API data fetching
import { useState, useEffect } from 'react';
import { apiClient } from '../utils/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// Hook for fetching data from API endpoints
export const useApi = <T>(endpoint: string, dependencies: any[] = []) => {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  // Function to fetch data from API
  const fetchData = async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const data = await apiClient.get<T>(endpoint);
      setState({ data, loading: false, error: null });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error instanceof Error ? error.message : 'An error occurred',
      });
    }
  };

  // Fetch data when component mounts or dependencies change
  useEffect(() => {
    fetchData();
  }, dependencies);

  // Return state and refetch function
  return {
    ...state,
    refetch: fetchData,
  };
};`
            }
          ]
        },
        {
          id: 'app',
          name: 'App.tsx',
          type: 'file',
          path: '/src/App.tsx',
          language: 'typescript',
          content: `// Main application component
import React from 'react';
import { Header } from './components/Header';
import { UserProfile } from './components/UserProfile';
import { ProductList } from './components/ProductList';

// Root App component that renders the main layout
function App() {
  // Handle mobile menu toggle
  const handleMenuToggle = () => {
    console.log('Menu toggled');
  };

  // Handle search functionality
  const handleSearch = (query: string) => {
    console.log('Search query:', query);
    // TODO: Implement actual search logic
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header onMenuToggle={handleMenuToggle} onSearch={handleSearch} />
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <UserProfile />
          <div>
            <ProductList />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;`
        },
        {
          id: 'main',
          name: 'main.tsx',
          type: 'file',
          path: '/src/main.tsx',
          language: 'typescript',
          content: `// Application entry point
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Render the main App component
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);`
        }
      ]
    },
    {
      id: 'public',
      name: 'public',
      type: 'folder',
      path: '/public',
      children: [
        {
          id: 'index',
          name: 'index.html',
          type: 'file',
          path: '/public/index.html',
          language: 'html',
          content: `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>My React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>`
        }
      ]
    },
    {
      id: 'package',
      name: 'package.json',
      type: 'file',
      path: '/package.json',
      language: 'json',
      content: `{
  "name": "searchable-codebase",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "lucide-react": "^0.263.1",
    "typescript": "^4.9.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "vite": "^4.0.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }
}`
    },
    {
      id: 'tsconfig',
      name: 'tsconfig.json',
      type: 'file',
      path: '/tsconfig.json',
      language: 'json',
      content: `{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}`
    },
    {
      id: 'viteconfig',
      name: 'vite.config.ts',
      type: 'file',
      path: '/vite.config.ts',
      language: 'typescript',
      content: `// Vite configuration file
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config with React plugin
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});`
    }
  ]
};

// Enhanced mock vector embeddings for the searchable codebase
export const mockEmbeddings: CodeEmbedding[] = [
  {
    id: '1',
    content: '// Main header component that handles navigation and search\nexport const Header: React.FC<HeaderProps> = ({ onMenuToggle, onSearch }) => {',
    embedding: [0.1, 0.2, 0.3, 0.4, 0.5],
    metadata: {
      fileName: 'Header.tsx',
      filePath: '/src/components/Header.tsx',
      language: 'typescript',
      functionName: 'Header',
      lineStart: 9,
      lineEnd: 10
    }
  },
  {
    id: '2',
    content: 'const handleSubmit = (e: React.FormEvent) => {\n    e.preventDefault();\n    const formData = new FormData(e.target as HTMLFormElement);\n    const query = formData.get(\'search\') as string;\n    onSearch(query);\n  };',
    embedding: [0.2, 0.1, 0.4, 0.3, 0.6],
    metadata: {
      fileName: 'Header.tsx',
      filePath: '/src/components/Header.tsx',
      language: 'typescript',
      functionName: 'handleSubmit',
      lineStart: 11,
      lineEnd: 16
    }
  },
  {
    id: '3',
    content: '// Async function to fetch user data from API\n  const fetchUserData = async () => {\n    try {\n      setLoading(true);\n      const userData = await mockApiCall();\n      setUser(userData);',
    embedding: [0.3, 0.4, 0.1, 0.2, 0.5],
    metadata: {
      fileName: 'UserProfile.tsx',
      filePath: '/src/components/UserProfile.tsx',
      language: 'typescript',
      functionName: 'fetchUserData',
      lineStart: 23,
      lineEnd: 32
    }
  },
  {
    id: '4',
    content: '// Email validation using regex pattern\nexport const validateEmail = (email: string): boolean => {\n  const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;\n  return emailRegex.test(email);\n};',
    embedding: [0.4, 0.3, 0.2, 0.1, 0.7],
    metadata: {
      fileName: 'validation.ts',
      filePath: '/src/utils/validation.ts',
      language: 'typescript',
      functionName: 'validateEmail',
      lineStart: 3,
      lineEnd: 7
    }
  },
  {
    id: '5',
    content: '// GET request method\n  async get<T>(endpoint: string): Promise<T> {\n    const response = await fetch(`${API_BASE_URL}${endpoint}`);\n    if (!response.ok) {\n      throw new ApiError(response.status, `GET ${endpoint} failed`);\n    }\n    return response.json();\n  },',
    embedding: [0.5, 0.6, 0.3, 0.2, 0.4],
    metadata: {
      fileName: 'api.ts',
      filePath: '/src/utils/api.ts',
      language: 'typescript',
      functionName: 'get',
      lineStart: 13,
      lineEnd: 21
    }
  },
  {
    id: '6',
    content: '// Component that displays a list of products with filtering\nexport const ProductList: React.FC = () => {\n  const [products] = useState<Product[]>([',
    embedding: [0.6, 0.4, 0.5, 0.3, 0.8],
    metadata: {
      fileName: 'ProductList.tsx',
      filePath: '/src/components/ProductList.tsx',
      language: 'typescript',
      functionName: 'ProductList',
      lineStart: 15,
      lineEnd: 17
    }
  },
  {
    id: '7',
    content: '// Filter and sort products based on user selection\n  const filteredProducts = useMemo(() => {\n    let filtered = products;\n    \n    if (filter !== \'all\') {\n      filtered = products.filter(product => \n        filter === \'inStock\' ? product.inStock : product.category.toLowerCase() === filter\n      );\n    }',
    embedding: [0.7, 0.5, 0.4, 0.6, 0.3],
    metadata: {
      fileName: 'ProductList.tsx',
      filePath: '/src/components/ProductList.tsx',
      language: 'typescript',
      functionName: 'filteredProducts',
      lineStart: 40,
      lineEnd: 48
    }
  },
  {
    id: '8',
    content: '// Hook that syncs state with localStorage\nexport const useLocalStorage = <T>(key: string, initialValue: T) => {\n  // Get value from localStorage or use initial value\n  const [storedValue, setStoredValue] = useState<T>(() => {',
    embedding: [0.8, 0.3, 0.6, 0.4, 0.7],
    metadata: {
      fileName: 'useLocalStorage.ts',
      filePath: '/src/hooks/useLocalStorage.ts',
      language: 'typescript',
      functionName: 'useLocalStorage',
      lineStart: 4,
      lineEnd: 7
    }
  },
  {
    id: '9',
    content: '// Format currency values for display\nexport const formatCurrency = (amount: number, currency: string = \'USD\'): string => {\n  return new Intl.NumberFormat(\'en-US\', {\n    style: \'currency\',\n    currency: currency,\n  }).format(amount);\n};',
    embedding: [0.9, 0.2, 0.7, 0.5, 0.6],
    metadata: {
      fileName: 'helpers.ts',
      filePath: '/src/utils/helpers.ts',
      language: 'typescript',
      functionName: 'formatCurrency',
      lineStart: 3,
      lineEnd: 9
    }
  },
  {
    id: '10',
    content: '// Hook for fetching data from API endpoints\nexport const useApi = <T>(endpoint: string, dependencies: any[] = []) => {\n  const [state, setState] = useState<UseApiState<T>>({\n    data: null,\n    loading: true,\n    error: null,\n  });',
    embedding: [0.3, 0.8, 0.4, 0.7, 0.5],
    metadata: {
      fileName: 'useApi.ts',
      filePath: '/src/hooks/useApi.ts',
      language: 'typescript',
      functionName: 'useApi',
      lineStart: 11,
      lineEnd: 17
    }
  }
];