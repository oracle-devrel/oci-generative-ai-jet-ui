import React, { useState } from 'react';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Database } from 'lucide-react';
import { FileNode } from '../types';

interface FileTreeProps {
  node: FileNode;
  depth?: number;
  onFileClick?: (path: string) => void;
}

const FileTreeNode: React.FC<FileTreeProps> = ({ node, depth = 0, onFileClick }) => {
  const [isExpanded, setIsExpanded] = useState(depth < 2);
  
  const handleToggle = () => {
    if (node.type === 'folder') {
      setIsExpanded(!isExpanded);
    }
  };

  const getFileIcon = (fileName: string) => {
    if (fileName.endsWith('.tsx') || fileName.endsWith('.ts')) return '⚛️';
    if (fileName.endsWith('.js') || fileName.endsWith('.jsx')) return '📄';
    if (fileName.endsWith('.json')) return '📋';
    if (fileName.endsWith('.css') || fileName.endsWith('.scss')) return '🎨';
    if (fileName.endsWith('.py')) return '🐍';
    return '📄';
  };

  return (
    <div className="select-none">
      <div
        className="flex items-center gap-2 px-3 py-2 hover:bg-white/10 cursor-pointer rounded-lg transition-colors text-white/90 hover:text-white"
        style={{ paddingLeft: `${depth * 16 + 12}px` }}
        onClick={() => {
          if (node.type === 'folder') {
            handleToggle();
          } else {
            onFileClick?.(node.path);
          }
        }}
      >
        {node.type === 'folder' ? (
          <>
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-blue-200" />
            ) : (
              <ChevronRight className="w-4 h-4 text-blue-200" />
            )}
            {isExpanded ? (
              <FolderOpen className="w-4 h-4 text-blue-300" />
            ) : (
              <Folder className="w-4 h-4 text-blue-300" />
            )}
          </>
        ) : (
          <>
            <div className="w-4 h-4" />
            <span className="text-sm">{getFileIcon(node.name)}</span>
          </>
        )}
        <span className="text-sm truncate font-medium">
          {node.name}
        </span>
      </div>
      
      {node.type === 'folder' && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onFileClick={onFileClick}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const FileTree: React.FC<Omit<FileTreeProps, 'depth'>> = (props) => {
  return (
    <div className="h-full overflow-y-auto bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Database className="w-6 h-6 text-blue-400" />
          <div>
            <h2 className="text-lg font-semibold text-white">Codebase Explorer</h2>
            <p className="text-xs text-blue-200">Searchable files & functions</p>
          </div>
        </div>
      </div>
      <div className="p-2">
        <FileTreeNode {...props} />
      </div>
    </div>
  );
};
