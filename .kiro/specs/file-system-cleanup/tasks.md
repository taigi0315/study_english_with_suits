# Implementation Plan: File System Cleanup

## Overview

This implementation plan converts the file system cleanup design into discrete coding tasks that build incrementally. The approach focuses on creating core components first, then integrating them into the existing LangFlix system, and finally adding comprehensive testing and cleanup policies.

## Tasks

- [x] 1. Create core data models and enums
  - Create JobContext, JobManifest, DirectoryStructure, and CleanupPolicy dataclasses
  - Define FileType, DirectoryType, and JobType enums
  - Add validation methods to data models
  - _Requirements: 3.1, 5.1_

- [ ]* 1.1 Write property tests for data models
  - **Property 5: Manifest Lifecycle Management**
  - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [ ] 2. Implement ManifestTracker component
  - [ ] 2.1 Create ManifestTracker class with file and directory tracking
    - Implement create_manifest, add_file, add_directory methods
    - Add JSON serialization/deserialization for manifests
    - Include manifest validation and corruption handling
    - _Requirements: 3.1, 3.2_

  - [ ]* 2.2 Write property tests for ManifestTracker
    - **Property 5: Manifest Lifecycle Management**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

  - [ ] 2.3 Add manifest backup and recovery mechanisms
    - Implement automatic manifest backup creation
    - Add fallback to directory scanning when manifests are corrupted
    - _Requirements: 3.4, 3.5_

- [ ] 3. Implement DirectoryManager component
  - [ ] 3.1 Create DirectoryManager class with intelligent directory creation
    - Implement create_job_directories and should_create_directory methods
    - Add logic to create only necessary directories based on job type
    - Include simplified directory structure generation
    - _Requirements: 1.1, 1.2, 1.4_

  - [ ]* 3.2 Write property tests for DirectoryManager
    - **Property 1: Conditional Directory Creation**
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 3.3 Write property tests for directory naming
    - **Property 4: Directory Naming Consistency**
    - **Validates: Requirements 1.4**

- [ ] 4. Implement CleanupService component
  - [ ] 4.1 Create CleanupService class with basic cleanup operations
    - Implement cleanup_job method with success/failure handling
    - Add manifest-driven file removal logic
    - Include error logging for failed cleanup operations
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.3, 3.5_

  - [ ]* 4.2 Write property tests for successful job cleanup
    - **Property 2: Successful Job Cleanup**
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ]* 4.3 Write property tests for failed job preservation
    - **Property 3: Failed Job Preservation**
    - **Validates: Requirements 2.4**

  - [ ] 4.4 Add age-based and manual cleanup methods
    - Implement cleanup_by_age for retention period enforcement
    - Add manual_cleanup method for administrative use
    - Include dry-run capability for manual cleanup
    - _Requirements: 2.5, 4.5_

  - [ ]* 4.5 Write property tests for cleanup error logging
    - **Property 8: Cleanup Error Logging**
    - **Validates: Requirements 3.5**

- [ ] 5. Implement JobManager component
  - [ ] 5.1 Create JobManager class with job lifecycle management
    - Implement start_job, complete_job, and get_job_context methods
    - Add integration with ManifestTracker and DirectoryManager
    - Include job context persistence and recovery
    - _Requirements: 1.3, 3.1, 3.4_

  - [ ]* 5.2 Write property tests for job lifecycle
    - **Property 5: Manifest Lifecycle Management**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

- [ ] 6. Implement Configuration Manager
  - [ ] 6.1 Create configuration system for cleanup policies
    - Add cleanup policy configuration to settings.py
    - Implement CleanupPolicy loading from YAML configuration
    - Include validation and default values for all policy options
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 6.2 Write property tests for configuration policy respect
    - **Property 6: Configuration Policy Respect**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [ ]* 6.3 Write property tests for retention period enforcement
    - **Property 9: Retention Period Enforcement**
    - **Validates: Requirements 2.5**

- [ ] 7. Checkpoint - Ensure all core components pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Integrate with existing ShortFormCreator
  - [ ] 8.1 Modify ShortFormCreator to use JobManager
    - Replace direct temp file management with JobManager integration
    - Update _register_temp_file to use ManifestTracker
    - Modify cleanup_temp_files to use CleanupService
    - _Requirements: 2.1, 2.2, 2.3, 3.2_

  - [ ]* 8.2 Write integration tests for ShortFormCreator
    - Test that ShortFormCreator properly integrates with new cleanup system
    - Verify temp files are tracked and cleaned up correctly
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 9. Integrate with existing OutputManager
  - [ ] 9.1 Update OutputManager to use simplified directory structure
    - Modify create_language_structure to use DirectoryManager
    - Update directory creation logic to be conditional based on job type
    - Ensure backward compatibility with existing path mappings
    - _Requirements: 1.1, 1.2, 5.1, 5.2, 5.3, 5.5_

  - [ ]* 9.2 Write property tests for output structure organization
    - **Property 10: Output Structure Organization**
    - **Validates: Requirements 5.1, 5.2, 5.3**

  - [ ]* 9.3 Write property tests for backward compatibility
    - **Property 12: Backward Compatibility Preservation**
    - **Validates: Requirements 5.5**

- [ ] 10. Add job status indication to directory structure
  - [ ] 10.1 Implement job status directory naming
    - Add status indicators to directory names (e.g., _processing, _completed, _failed)
    - Update DirectoryManager to include status in directory creation
    - Add status update methods to JobManager
    - _Requirements: 5.4_

  - [ ]* 10.2 Write property tests for job status indication
    - **Property 11: Job Status Directory Indication**
    - **Validates: Requirements 5.4**

- [ ] 11. Add manual cleanup commands
  - [ ] 11.1 Create CLI commands for manual cleanup
    - Add cleanup commands to existing CLI interface
    - Implement pattern-based cleanup with dry-run support
    - Include administrative cleanup utilities
    - _Requirements: 4.5_

  - [ ]* 11.2 Write property tests for manual cleanup
    - **Property 7: Manual Cleanup Availability**
    - **Validates: Requirements 4.5**

- [ ] 12. Update existing video processing components
  - [ ] 12.1 Integrate JobManager with video_editor.py
    - Replace existing temp file tracking with JobManager
    - Update cleanup methods to use CleanupService
    - Ensure proper job lifecycle management
    - _Requirements: 2.1, 2.2, 2.3, 3.2_

  - [ ] 12.2 Update video_factory.py and other video processing services
    - Integrate JobManager with video factory and processing services
    - Replace direct temp file management with manifest tracking
    - Update cleanup calls throughout the video processing pipeline
    - _Requirements: 2.1, 2.2, 2.3, 3.2_

- [ ] 13. Add configuration file updates
  - [ ] 13.1 Update default.yaml with cleanup configuration
    - Add cleanup policy section to configuration
    - Include default values for all cleanup options
    - Add documentation comments for configuration options
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ] 13.2 Update settings.py with cleanup accessors
    - Add getter methods for cleanup configuration
    - Include validation and default value handling
    - Add debug mode integration for cleanup disable
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 14. Final integration and testing
  - [ ] 14.1 Create end-to-end integration tests
    - Test complete video generation workflow with new cleanup system
    - Verify proper file tracking and cleanup across all components
    - Test both success and failure scenarios
    - _Requirements: All requirements_

  - [ ]* 14.2 Write comprehensive property tests for the complete system
    - Test all properties together in integrated scenarios
    - Verify system behavior across various job types and configurations
    - _Requirements: All requirements_

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration focuses on existing component compatibility
- The implementation maintains backward compatibility while providing new cleanup capabilities