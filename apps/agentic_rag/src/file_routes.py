"""
File upload and management API routes.

Provides endpoints for:
- File upload with storage mode selection
- File listing and management
- Temporary file cleanup
"""

import uuid
import shutil
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .file_handler import FileHandler, _temporary_files

# Router for file management
router = APIRouter(prefix="/v1/files", tags=["Files"])

# Global file handler (initialized in main.py)
_file_handler: Optional[FileHandler] = None


def init_file_routes(file_handler: FileHandler):
    """Initialize file routes with the file handler."""
    global _file_handler
    _file_handler = file_handler


class FileUploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    file_id: Optional[str] = None
    filename: str
    storage_mode: str  # "temporary" or "permanent"
    collection: Optional[str] = None
    chunks_processed: int = 0
    message: str


class FileInfo(BaseModel):
    """Model for file information."""
    file_id: Optional[str] = None
    filename: str
    path: Optional[str] = None
    file_type: str
    size_bytes: int
    storage_mode: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None


@router.post("", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    storage_mode: str = Form("temporary"),  # "temporary" or "permanent"
    collection: str = Form("general"),  # pdf, web, repository, general
):
    """
    Upload a file for RAG processing.

    Args:
        file: The file to upload
        storage_mode: "temporary" (context only) or "permanent" (add to RAG)
        collection: Target collection for permanent storage
    """
    if not _file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")

    # Check file type
    if not _file_handler.is_supported(file.filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {Path(file.filename).suffix}"
        )

    # Save uploaded file temporarily
    temp_dir = Path("./temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        if storage_mode == "permanent":
            # Add to RAG vector store
            collection_map = {
                "pdf": "PDFCOLLECTION",
                "web": "WEBCOLLECTION",
                "repository": "REPOCOLLECTION",
                "repo": "REPOCOLLECTION",
                "general": "GENERALCOLLECTION",
            }
            target_collection = collection_map.get(collection.lower(), "GENERALCOLLECTION")

            result = _file_handler.add_to_rag(temp_path, target_collection)

            # Also save to documents directory for future @file references
            dest_path = _file_handler.documents_dir / file.filename
            if not dest_path.exists():
                shutil.copy(temp_path, dest_path)

            return FileUploadResponse(
                success=True,
                file_id=result.get("document_id"),
                filename=file.filename,
                storage_mode="permanent",
                collection=target_collection,
                chunks_processed=result.get("chunks_stored", len(result.get("chunks", []))),
                message=f"File added to {target_collection} with {result.get('chunks_stored', 0)} chunks"
            )

        else:
            # Store temporarily
            result = _file_handler.add_temporary(temp_path)

            return FileUploadResponse(
                success=True,
                file_id=result.get("file_id"),
                filename=file.filename,
                storage_mode="temporary",
                chunks_processed=len(result.get("chunks", [])),
                message="File stored temporarily for context injection"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("", response_model=List[FileInfo])
async def list_files(
    storage_mode: Optional[str] = Query(None, description="Filter by storage mode"),
    include_documents: bool = Query(True, description="Include files in documents directory"),
):
    """
    List available files.

    Returns files from:
    - Temporary storage (uploaded for context)
    - Documents directory (available for @file references)
    """
    if not _file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")

    files = []

    # Add temporary files
    if storage_mode in [None, "temporary"]:
        for temp_file in _file_handler.list_temporary_files():
            files.append(FileInfo(
                file_id=temp_file["file_id"],
                filename=temp_file["filename"],
                file_type=_file_handler.get_file_type(temp_file["filename"]),
                size_bytes=temp_file["size_bytes"],
                storage_mode="temporary",
                created=temp_file["created"],
            ))

    # Add documents directory files
    if include_documents and storage_mode in [None, "documents"]:
        for doc_file in _file_handler.list_documents_dir():
            files.append(FileInfo(
                filename=doc_file["filename"],
                path=doc_file["path"],
                file_type=doc_file["file_type"],
                size_bytes=doc_file["size_bytes"],
                storage_mode="documents",
                modified=doc_file["modified"],
            ))

    return files


@router.get("/{file_id}")
async def get_file(file_id: str):
    """Get information about a specific temporary file."""
    if file_id not in _temporary_files:
        raise HTTPException(status_code=404, detail="File not found")

    data = _temporary_files[file_id]
    return {
        "file_id": file_id,
        "filename": data["metadata"]["filename"],
        "file_type": data["metadata"]["file_type"],
        "size_bytes": data["metadata"]["size_bytes"],
        "created": data["created"],
        "content_preview": data["content"][:500] + "..." if len(data["content"]) > 500 else data["content"],
        "chunks_count": len(data["chunks"]),
    }


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a temporary file."""
    if not _file_handler:
        raise HTTPException(status_code=503, detail="File handler not initialized")

    if _file_handler.remove_temporary(file_id):
        return {"success": True, "message": f"File {file_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="File not found")


@router.delete("")
async def clear_temporary_files():
    """Clear all temporary files."""
    count = len(_temporary_files)
    _temporary_files.clear()
    return {"success": True, "message": f"Cleared {count} temporary files"}


# Upload page HTML
UPLOAD_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document Upload - Agentic RAG</title>
    <style>
        :root {
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --error: #ef4444;
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-2: #334155;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #475569;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
        }

        .container {
            max-width: 600px;
            margin: 0 auto;
        }

        h1 {
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .subtitle {
            color: var(--text-muted);
            margin-bottom: 2rem;
        }

        .upload-card {
            background: var(--surface);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid var(--border);
        }

        .drop-zone {
            border: 2px dashed var(--border);
            border-radius: 8px;
            padding: 3rem 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 1.5rem;
        }

        .drop-zone:hover, .drop-zone.dragover {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.1);
        }

        .drop-zone-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }

        .drop-zone-text {
            color: var(--text-muted);
        }

        .drop-zone-text strong {
            color: var(--primary);
        }

        .file-input {
            display: none;
        }

        .selected-file {
            display: none;
            background: var(--surface-2);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            align-items: center;
            gap: 1rem;
        }

        .selected-file.visible {
            display: flex;
        }

        .file-icon {
            font-size: 2rem;
        }

        .file-info {
            flex: 1;
        }

        .file-name {
            font-weight: 500;
            word-break: break-all;
        }

        .file-size {
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        .remove-file {
            background: none;
            border: none;
            color: var(--error);
            cursor: pointer;
            font-size: 1.5rem;
            padding: 0.25rem;
        }

        .options {
            margin-bottom: 1.5rem;
        }

        .option-group {
            margin-bottom: 1rem;
        }

        .option-label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }

        .radio-group {
            display: flex;
            gap: 1rem;
        }

        .radio-option {
            flex: 1;
            position: relative;
        }

        .radio-option input {
            position: absolute;
            opacity: 0;
        }

        .radio-option label {
            display: block;
            padding: 1rem;
            background: var(--surface-2);
            border: 2px solid var(--border);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            text-align: center;
        }

        .radio-option input:checked + label {
            border-color: var(--primary);
            background: rgba(99, 102, 241, 0.1);
        }

        .radio-option label:hover {
            border-color: var(--primary);
        }

        .radio-title {
            font-weight: 500;
            margin-bottom: 0.25rem;
        }

        .radio-desc {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .collection-select {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 1rem;
            cursor: pointer;
        }

        .collection-select:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .upload-btn {
            width: 100%;
            padding: 1rem;
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }

        .upload-btn:hover:not(:disabled) {
            background: var(--primary-hover);
        }

        .upload-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .status {
            margin-top: 1.5rem;
            padding: 1rem;
            border-radius: 8px;
            display: none;
        }

        .status.visible {
            display: block;
        }

        .status.success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--success);
            color: var(--success);
        }

        .status.error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--error);
            color: var(--error);
        }

        .status.loading {
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid var(--primary);
            color: var(--primary);
        }

        .files-section {
            margin-top: 2rem;
        }

        .files-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .files-title {
            font-size: 1.25rem;
            font-weight: 500;
        }

        .refresh-btn {
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
        }

        .files-list {
            background: var(--surface);
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow: hidden;
        }

        .file-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            gap: 1rem;
        }

        .file-item:last-child {
            border-bottom: none;
        }

        .file-item-icon {
            font-size: 1.5rem;
        }

        .file-item-info {
            flex: 1;
        }

        .file-item-name {
            font-weight: 500;
        }

        .file-item-meta {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .file-item-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge-temporary {
            background: rgba(99, 102, 241, 0.2);
            color: var(--primary);
        }

        .badge-documents {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
        }

        .empty-state {
            padding: 2rem;
            text-align: center;
            color: var(--text-muted);
        }

        .tip {
            margin-top: 2rem;
            padding: 1rem;
            background: var(--surface);
            border-radius: 8px;
            border-left: 3px solid var(--primary);
        }

        .tip-title {
            font-weight: 500;
            margin-bottom: 0.5rem;
        }

        .tip-code {
            font-family: monospace;
            background: var(--surface-2);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 Document Upload</h1>
        <p class="subtitle">Upload documents for RAG processing or temporary context</p>

        <div class="upload-card">
            <div class="drop-zone" id="dropZone">
                <div class="drop-zone-icon">📁</div>
                <p class="drop-zone-text">
                    Drag & drop a file here, or <strong>click to browse</strong>
                </p>
                <p class="drop-zone-text" style="font-size: 0.75rem; margin-top: 0.5rem;">
                    Supports: PDF, TXT, MD, PY, JS, JSON, and more
                </p>
            </div>
            <input type="file" class="file-input" id="fileInput" accept=".pdf,.txt,.md,.py,.js,.ts,.json,.yaml,.yml,.html,.css,.sql,.java,.go,.rs,.rb,.c,.cpp,.h">

            <div class="selected-file" id="selectedFile">
                <span class="file-icon">📄</span>
                <div class="file-info">
                    <div class="file-name" id="fileName"></div>
                    <div class="file-size" id="fileSize"></div>
                </div>
                <button class="remove-file" id="removeFile">&times;</button>
            </div>

            <div class="options">
                <div class="option-group">
                    <span class="option-label">Storage Mode</span>
                    <div class="radio-group">
                        <div class="radio-option">
                            <input type="radio" name="storage" id="temporary" value="temporary" checked>
                            <label for="temporary">
                                <div class="radio-title">📎 Temporary</div>
                                <div class="radio-desc">Context for current session</div>
                            </label>
                        </div>
                        <div class="radio-option">
                            <input type="radio" name="storage" id="permanent" value="permanent">
                            <label for="permanent">
                                <div class="radio-title">💾 Permanent</div>
                                <div class="radio-desc">Add to RAG knowledge base</div>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="option-group" id="collectionGroup" style="display: none;">
                    <span class="option-label">Collection</span>
                    <select class="collection-select" id="collection">
                        <option value="general">General Knowledge</option>
                        <option value="pdf">PDF Documents</option>
                        <option value="web">Web Content</option>
                        <option value="repository">Code Repository</option>
                    </select>
                </div>
            </div>

            <button class="upload-btn" id="uploadBtn" disabled>Upload Document</button>

            <div class="status" id="status"></div>
        </div>

        <div class="files-section">
            <div class="files-header">
                <h2 class="files-title">Available Files</h2>
                <button class="refresh-btn" id="refreshBtn">🔄 Refresh</button>
            </div>
            <div class="files-list" id="filesList">
                <div class="empty-state">Loading files...</div>
            </div>
        </div>

        <div class="tip">
            <div class="tip-title">💡 Tip: Reference files in chat</div>
            <p>Use <span class="tip-code">@filename.pdf</span> for temporary context or <span class="tip-code">@@filename.pdf</span> to add to RAG storage directly from chat.</p>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const selectedFile = document.getElementById('selectedFile');
        const fileName = document.getElementById('fileName');
        const fileSize = document.getElementById('fileSize');
        const removeFile = document.getElementById('removeFile');
        const uploadBtn = document.getElementById('uploadBtn');
        const status = document.getElementById('status');
        const collectionGroup = document.getElementById('collectionGroup');
        const filesList = document.getElementById('filesList');
        const refreshBtn = document.getElementById('refreshBtn');

        let currentFile = null;

        // Storage mode toggle
        document.querySelectorAll('input[name="storage"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                collectionGroup.style.display = e.target.value === 'permanent' ? 'block' : 'none';
            });
        });

        // Drop zone events
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleFile(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleFile(e.target.files[0]);
            }
        });

        removeFile.addEventListener('click', () => {
            currentFile = null;
            selectedFile.classList.remove('visible');
            uploadBtn.disabled = true;
            fileInput.value = '';
        });

        function handleFile(file) {
            currentFile = file;
            fileName.textContent = file.name;
            fileSize.textContent = formatBytes(file.size);
            selectedFile.classList.add('visible');
            uploadBtn.disabled = false;
            status.classList.remove('visible');
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        uploadBtn.addEventListener('click', async () => {
            if (!currentFile) return;

            const storageMode = document.querySelector('input[name="storage"]:checked').value;
            const collection = document.getElementById('collection').value;

            const formData = new FormData();
            formData.append('file', currentFile);
            formData.append('storage_mode', storageMode);
            formData.append('collection', collection);

            uploadBtn.disabled = true;
            showStatus('Uploading...', 'loading');

            try {
                const response = await fetch('/v1/files', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    showStatus(`✅ ${result.message}`, 'success');
                    currentFile = null;
                    selectedFile.classList.remove('visible');
                    fileInput.value = '';
                    loadFiles();
                } else {
                    showStatus(`❌ ${result.detail || 'Upload failed'}`, 'error');
                    uploadBtn.disabled = false;
                }
            } catch (error) {
                showStatus(`❌ ${error.message}`, 'error');
                uploadBtn.disabled = false;
            }
        });

        function showStatus(message, type) {
            status.textContent = message;
            status.className = `status visible ${type}`;
        }

        async function loadFiles() {
            try {
                const response = await fetch('/v1/files');
                const files = await response.json();

                if (files.length === 0) {
                    filesList.innerHTML = '<div class="empty-state">No files uploaded yet</div>';
                    return;
                }

                filesList.innerHTML = files.map(file => `
                    <div class="file-item">
                        <span class="file-item-icon">${getFileIcon(file.file_type)}</span>
                        <div class="file-item-info">
                            <div class="file-item-name">${file.filename}</div>
                            <div class="file-item-meta">${formatBytes(file.size_bytes)} • ${file.file_type}</div>
                        </div>
                        <span class="file-item-badge ${file.storage_mode === 'temporary' ? 'badge-temporary' : 'badge-documents'}">
                            ${file.storage_mode === 'temporary' ? '📎 Temporary' : '📁 Documents'}
                        </span>
                    </div>
                `).join('');
            } catch (error) {
                filesList.innerHTML = `<div class="empty-state">Error loading files: ${error.message}</div>`;
            }
        }

        function getFileIcon(fileType) {
            const icons = {
                'pdf': '📕',
                'text': '📄',
                'markdown': '📝',
                'code': '💻',
            };
            return icons[fileType] || '📄';
        }

        refreshBtn.addEventListener('click', loadFiles);

        // Initial load
        loadFiles();
    </script>
</body>
</html>
"""


# Upload page route (served at /upload, not under /v1/files)
upload_page_router = APIRouter(tags=["Upload Page"])


@upload_page_router.get("/upload", response_class=HTMLResponse)
async def upload_page():
    """Serve the file upload page."""
    return HTMLResponse(content=UPLOAD_PAGE_HTML)
