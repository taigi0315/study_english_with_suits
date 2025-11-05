# [TICKET-028] Implement File Management API Endpoints

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Feature Enhancement

## Impact Assessment
**Business Impact:**
- Users cannot view file details through API
- Users cannot delete files through API
- File management must be done manually or through other interfaces
- Reduces API completeness and usability

**Technical Impact:**
- Affects `langflix/api/routes/files.py` - 2 endpoints need implementation
- `GET /api/files/{file_id}` - Currently returns mock data
- `DELETE /api/files/{file_id}` - Currently returns mock response
- Requires proper file path resolution and validation
- Requires integration with storage backend (local or GCS)

**Effort Estimate:**
- Small (< 1 day)
  - File details: 2-3 hours
  - File deletion: 2-3 hours
  - Testing: 1-2 hours

## Problem Description

### Current State
**Location:** `langflix/api/routes/files.py:35-55`

The file management API has incomplete implementations:

1. **GET /api/files/{file_id}** (`get_file_details`):
```python
@router.get("/files/{file_id}")
async def get_file_details(file_id: str) -> Dict[str, Any]:
    """Get file details."""
    
    # TODO: Implement file details lookup
    return {
        "file_id": file_id,
        "name": "example.mp4",
        "path": "output/example.mp4",
        "size": 1024000,
        "type": "video/mp4"
    }
```

**Problems:**
- Returns hardcoded mock data
- Does not actually look up file by ID
- Does not resolve file path from ID
- Does not validate file existence
- Does not use storage backend abstraction

2. **DELETE /api/files/{file_id}** (`delete_file`):
```python
@router.delete("/files/{file_id}")
async def delete_file(file_id: str) -> Dict[str, Any]:
    """Delete a file."""
    
    # TODO: Implement file deletion
    return {
        "message": f"File {file_id} deleted successfully"
    }
```

**Problems:**
- Does not actually delete files
- Returns success message without performing operation
- No validation of file existence
- No security checks (could allow deleting important files)
- No integration with storage backend

### Root Cause Analysis
- Initial API scaffolding created with placeholder implementations
- File management was not prioritized in initial development
- Storage backend abstraction exists but not used in file routes
- No clear file ID mapping strategy defined

### Evidence
- `langflix/api/routes/files.py:39` - TODO comment for file details
- `langflix/api/routes/files.py:52` - TODO comment for file deletion
- `langflix/storage/` - Storage backend abstraction exists but not used
- `langflix/api/routes/files.py:12-33` - `list_files()` is implemented but uses hardcoded "output" path

## Proposed Solution

### Approach
1. **File ID Resolution**: Map file_id to actual file path
   - Options: file_id is path, file_id is hash, or file_id is database ID
   - Current `list_files()` returns path, so use path as ID (simplest)
2. **Storage Backend Integration**: Use storage abstraction for file operations
3. **File Details**: Return actual file metadata (size, type, modified time, etc.)
4. **File Deletion**: Actually delete files with proper validation
5. **Security**: Add validation to prevent deleting critical files
6. **Error Handling**: Proper error responses for missing files, permission errors

### Implementation Details

#### 1. File ID Strategy
Since `list_files()` returns files with `path` field, use path as the file_id:
- `GET /api/files/{file_id}` where `file_id` is the relative path (e.g., `"Suits/S01E01/educational_video_1.mkv"`)
- `DELETE /api/files/{file_id}` same as above

#### 2. Update File Details Endpoint
```python
@router.get("/files/{file_id:path}")
async def get_file_details(
    file_id: str,
    storage: StorageBackend = Depends(get_storage)
) -> Dict[str, Any]:
    """
    Get file details by file path.
    
    Args:
        file_id: Relative file path (e.g., "Suits/S01E01/educational_video_1.mkv")
        storage: Storage backend instance
        
    Returns:
        File metadata including name, path, size, type, modified time
    """
    try:
        # Validate file path (prevent directory traversal)
        if ".." in file_id or file_id.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Check if file exists
        if not storage.file_exists(file_id):
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        # Get file metadata
        file_path = Path(storage.get_file_url(file_id))
        file_stat = file_path.stat()
        
        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"
        
        return {
            "file_id": file_id,
            "name": file_path.name,
            "path": file_id,
            "size": file_stat.st_size,
            "type": mime_type,
            "modified": file_stat.st_mtime,
            "created": file_stat.st_ctime,
            "is_directory": file_path.is_dir()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file details for {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving file details: {str(e)}")
```

#### 3. Update File Deletion Endpoint
```python
@router.delete("/files/{file_id:path}")
async def delete_file(
    file_id: str,
    storage: StorageBackend = Depends(get_storage)
) -> Dict[str, Any]:
    """
    Delete a file by file path.
    
    Args:
        file_id: Relative file path (e.g., "Suits/S01E01/educational_video_1.mkv")
        storage: Storage backend instance
        
    Returns:
        Success message with deleted file path
    """
    try:
        # Validate file path (prevent directory traversal)
        if ".." in file_id or file_id.startswith("/"):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        # Check if file exists
        if not storage.file_exists(file_id):
            raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
        
        # Security check: prevent deleting critical files
        # Define protected paths (config files, logs, etc.)
        protected_patterns = [
            "config.yaml",
            ".env",
            "*.log",
            "langflix.log",
            "requirements.txt"
        ]
        
        file_name = Path(file_id).name
        for pattern in protected_patterns:
            if pattern.startswith("*"):
                if file_name.endswith(pattern[1:]):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Cannot delete protected file: {file_id}"
                    )
            elif file_name == pattern:
                raise HTTPException(
                    status_code=403,
                    detail=f"Cannot delete protected file: {file_id}"
                )
        
        # Delete file using storage backend
        success = storage.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {file_id}")
        
        logger.info(f"File deleted: {file_id}")
        
        return {
            "message": f"File {file_id} deleted successfully",
            "file_id": file_id,
            "deleted": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
```

#### 4. Update list_files to Use Storage Backend
```python
@router.get("/files")
async def list_files(
    storage: StorageBackend = Depends(get_storage)
) -> Dict[str, Any]:
    """List all output files."""
    
    try:
        files = []
        # Use storage backend to list files (list all with empty prefix, then filter)
        # Note: list_files returns relative paths from base_path
        for file_path in storage.list_files(""):
            # Check if it's actually a file (not a directory)
            full_path = Path(storage.get_file_url(file_path))
            if full_path.is_file():
                file_stat = full_path.stat()
                files.append({
                    "name": full_path.name,
                    "path": file_path,
                    "size": file_stat.st_size,
                    "modified": file_stat.st_mtime
                })
        
        return {
            "files": files,
            "total": len(files)
        }
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")
```

### Alternative Approaches Considered
- Option 1: Use database IDs instead of paths - **Rejected** because requires database schema changes and more complexity
- Option 2: Use file hashes as IDs - **Rejected** because requires hashing all files, more complex lookup
- Option 3: Use relative paths as IDs (selected) - **Chosen** because simplest, aligns with existing `list_files()` response

### Benefits
- Complete API functionality for file management
- Consistent with storage backend abstraction
- Proper error handling and validation
- Security checks prevent accidental deletion of critical files
- Better user experience with actual file operations

### Risks & Considerations
- **Path Traversal**: Must validate file paths to prevent `../` attacks
- **Protected Files**: Must prevent deletion of critical system files
- **Storage Backend**: Must ensure storage backend methods exist (`file_exists`, `delete_file`, `get_file_url`, `list_files`, etc.)
- **Error Handling**: Must handle storage backend errors gracefully
- **Performance**: Listing files recursively could be slow for large directories

## Testing Strategy

### Unit Tests
- Test file path validation (reject `../`, absolute paths)
- Test file existence checking
- Test protected file patterns
- Test MIME type detection
- Test error handling for missing files

### Integration Tests
- Test full flow: list files → get details → delete file
- Test with both local and GCS storage backends
- Test deletion of actual files
- Test error cases (missing file, permission denied)

### Edge Cases
- File with special characters in name
- Very long file paths
- Files in nested directories
- Attempting to delete protected files
- Concurrent deletion attempts

## Files Affected

**Modified Files:**
- `langflix/api/routes/files.py` - Implement `get_file_details()` and `delete_file()` endpoints
- Update `list_files()` to use storage backend

**New Test Files:**
- `tests/unit/test_file_management_api.py` - Unit tests for file endpoints
- `tests/integration/test_file_management_integration.py` - Integration tests

**Updated Test Files:**
- `tests/integration/test_api_integration.py` - Add file management tests if exists

## Dependencies
- Depends on: Storage backend abstraction (`langflix/storage/`) - Already exists
- Blocks: None
- Related to: None

## References
- Current implementation: `langflix/api/routes/files.py`
- Storage backend: `langflix/storage/base.py`
- Storage factory: `langflix/storage/factory.py`
- API dependencies: `langflix/api/dependencies.py`

## Architect Review Questions
**For the architect to consider:**
1. Should file_id be a path or a database ID?
2. What files should be protected from deletion?
3. Should we add file upload endpoint as well?
4. Should we support batch deletion?
5. Do we need file permissions/authorization checks?

## Success Criteria
How do we know this is successfully implemented?
- [ ] `GET /api/files/{file_id}` returns actual file metadata
- [ ] `DELETE /api/files/{file_id}` actually deletes files
- [ ] Path traversal attacks are prevented
- [ ] Protected files cannot be deleted
- [ ] Storage backend abstraction is used consistently
- [ ] Error handling works for missing files, permission errors
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] API documentation updated

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **API Completeness**: File management is a basic CRUD operation that should be complete. Currently incomplete endpoints reduce API usability and force manual file operations.
- **Storage Abstraction Alignment**: The system already has a storage backend abstraction (ADR-011), but file routes don't use it. This ticket completes the abstraction usage pattern.
- **Security Foundation**: Proper file deletion with protection patterns sets foundation for future authorization features.
- **User Experience**: Complete API enables better frontend integration and user workflows.

**Implementation Phase:** Phase 2 - Sprint 2 (Weeks 3-4)
**Sequence Order:** #5 in implementation queue (after critical fixes and core features)

**Architectural Guidance:**
Key considerations for implementation:
- **Storage Backend Methods**: Use correct method names from `StorageBackend` interface:
  - `file_exists(remote_path)` not `exists()`
  - `delete_file(remote_path)` not `delete()`
  - `get_file_url(remote_path)` to get local path for metadata
  - `list_files(prefix)` - note: no `recursive` parameter, use empty prefix to list all
- **Path Validation**: Critical - validate paths to prevent directory traversal attacks. Current validation (`".."` check) is good but consider using `Path.resolve()` for stronger validation.
- **Protected Files Pattern**: Consider making protected patterns configurable via settings instead of hardcoded.
- **Error Handling**: Storage backend methods return `bool` for `delete_file()`, check return value. Handle `StorageError` exceptions from storage backend.
- **Performance**: For `list_files()`, listing all files recursively could be slow for large directories. Consider pagination or filtering options in future enhancements.

**Dependencies:**
- **Must complete first:** None (storage backend already exists)
- **Should complete first:** None
- **Blocks:** None
- **Related work:** ADR-011 (Storage Abstraction Layer), TICKET-010 (API Dependencies)

**Risk Mitigation:**
- **Risk:** Path traversal attacks
  - **Mitigation:** Validate paths (reject `../`, absolute paths). Consider using `Path.resolve()` and checking it's within base_path.
- **Risk:** Accidental deletion of important files
  - **Mitigation:** Protected file patterns prevent deletion of critical files. Consider expanding protection list.
- **Risk:** Storage backend methods not available
  - **Mitigation:** Verified storage backend interface - all required methods exist. Code examples updated to match actual interface.
- **Risk:** Performance issues with large file lists
  - **Mitigation:** Current implementation lists all files. For large directories, consider pagination in future enhancement.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Storage backend methods used correctly (`file_exists`, `delete_file`, `get_file_url`)
- [ ] Path validation prevents directory traversal attacks
- [ ] Protected file patterns work correctly
- [ ] Error handling covers storage backend exceptions
- [ ] Code follows existing API patterns (FastAPI, dependency injection)
- [ ] Documentation updated in `docs/api/README_eng.md` and `docs/api/README_kor.md`

**Alternative Approaches Considered:**
- **Original proposal:** Use file paths as IDs - **Selected** ✅ Simplest approach, aligns with existing `list_files()` response
- **Alternative 1:** Use database IDs for files - **Rejected** - Requires database schema changes, more complexity, not needed for current use case
- **Alternative 2:** Use file hashes as IDs - **Rejected** - Requires hashing all files, more complex lookup, unnecessary overhead
- **Alternative 3:** Don't implement file deletion, only details - **Rejected** - Incomplete API, users need deletion capability

**Implementation Notes:**
- Start by: Updating `get_file_details()` endpoint first (simpler, read-only)
- Then: Implement `delete_file()` with security checks
- Finally: Update `list_files()` to use storage backend
- Watch out for: Storage backend method names (`file_exists` not `exists`, `delete_file` not `delete`)
- Coordinate with: Verify storage backend interface matches implementation
- Reference: `langflix/storage/base.py` for interface, `langflix/storage/local.py` for implementation example
- Note: `list_files(prefix)` method signature - empty prefix lists all files, no recursive parameter needed

**Estimated Timeline:** 1 day (refined from Small estimate)
- File details endpoint: 2-3 hours
- File deletion endpoint: 2-3 hours  
- Update list_files: 1 hour
- Testing: 2-3 hours

**Recommended Owner:** Backend engineer familiar with FastAPI and storage abstraction

