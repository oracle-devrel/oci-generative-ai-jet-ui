import React, { useState, useEffect } from 'react';
import { Database, Info, X, RefreshCw } from 'lucide-react';
import { VectorIndexInfo } from '../types';

// at the top
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

interface VectorDBInfoProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VectorDBInfo: React.FC<VectorDBInfoProps> = ({ isOpen, onClose }) => {
  const [indexInfo, setIndexInfo] = useState<VectorIndexInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'info'>('info');


  useEffect(() => {
    if (isOpen) {
      loadIndexInfo();
    }
  }, [isOpen]);

  const loadIndexInfo = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/vector-db-info`);
      if (!res.ok) throw new Error(await res.text());
      const info: VectorIndexInfo = await res.json();
      setIndexInfo(info);
    } catch (error) {
      console.error('Failed to load index info:', error);
    } finally {
      setLoading(false);
    }
  };


  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Database className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  LangChain Vector Database
                </h3>
                <p className="text-sm text-gray-600">
                  Vector database index information
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="border-b border-gray-200">
          <div className="flex">
            <button className="flex items-center gap-2 px-6 py-4 font-medium text-blue-600 border-b-2 border-blue-600 bg-blue-50">
              <Info className="w-4 h-4" />
              Index Info
            </button>
          </div>
        </div>


        {/* Content */}
        <div className="p-6 overflow-auto max-h-[60vh]">
          {activeTab === 'info' && (
            <div className="space-y-6">
              {loading ? (
                <div className="text-center py-8">
                  <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-4" />
                  <p className="text-gray-600">Loading index information...</p>
                </div>
              ) : indexInfo ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-2">Index Details</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Name:</span>
                        <span className="font-mono">{indexInfo.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Dimension:</span>
                        <span className="font-mono">{indexInfo.dimension}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Metric:</span>
                        <span className="font-mono">{indexInfo.metric}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Total Vectors:</span>
                        <span className="font-mono">{indexInfo.totalVectors}</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="font-semibold text-gray-900 mb-2">Timestamps</h4>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-gray-600">Created:</span>
                        <div className="font-mono text-xs mt-1">
                          {new Date(indexInfo.createdAt).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-600">Last Updated:</span>
                        <div className="font-mono text-xs mt-1">
                          {new Date(indexInfo.lastUpdated).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  Failed to load index information
                </div>
              )}
            </div>
          )}

          {/* Footer */}
          <div className="p-6 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                <strong>LangChain Integration:</strong> Using Jina embedding model with a managed vector database service
              </div>
              <button
                onClick={onClose}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};