"""
Unit tests for error_handler integration into core modules.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock, call
from langflix.core.error_handler import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    get_error_handler
)


class TestErrorHandlerIntegration(unittest.TestCase):
    """Test error_handler integration with core modules."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global error handler
        import langflix.core.error_handler
        langflix.core.error_handler._error_handler = None
        
    def tearDown(self):
        """Clean up after tests."""
        # Reset global error handler
        import langflix.core.error_handler
        langflix.core.error_handler._error_handler = None
    
    def test_error_handler_decorator_catches_exceptions(self):
        """Test that handle_error_decorator catches and reports exceptions."""
        from langflix.core.error_handler import handle_error_decorator, ErrorContext
        
        @handle_error_decorator(
            ErrorContext(operation="test_op", component="test_component"),
            retry=False,
            fallback=False
        )
        def failing_function():
            raise ValueError("Test error")
        
        # Should raise the exception after logging
        with self.assertRaises(ValueError):
            failing_function()
        
        # Check that error was reported
        handler = get_error_handler()
        self.assertGreater(len(handler.error_reports), 0)
        self.assertEqual(handler.error_reports[-1].message, "Test error")
    
    def test_retry_on_error_decorator(self):
        """Test that retry_on_error decorator retries on failures."""
        from langflix.core.error_handler import retry_on_error
        
        attempt_count = [0]
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def flaky_function():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ConnectionError("Temporary error")
            return "success"
        
        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count[0], 3)
    
    def test_retry_on_error_raises_after_max_attempts(self):
        """Test that retry_on_error raises after max attempts."""
        from langflix.core.error_handler import retry_on_error
        
        @retry_on_error(max_attempts=2, delay=0.1)
        def always_failing():
            raise ValueError("Always fails")
        
        with self.assertRaises(ValueError) as context:
            always_failing()
        
        self.assertEqual(str(context.exception), "Always fails")
    
    def test_error_context_preserves_additional_data(self):
        """Test that ErrorContext preserves additional_data."""
        context = ErrorContext(
            operation="test_op",
            component="test_component",
            additional_data={"key1": "value1", "key2": 42}
        )
        
        self.assertEqual(context.additional_data["key1"], "value1")
        self.assertEqual(context.additional_data["key2"], 42)
    
    def test_expression_analyzer_error_reporting(self):
        """Test that expression_analyzer reports errors correctly."""
        from langflix.core.error_handler import handle_error, ErrorContext
        
        error_context = ErrorContext(
            operation="generate_content",
            component="expression_analyzer",
            additional_data={"max_retries": 3}
        )
        
        test_error = ConnectionError("API timeout")
        report = handle_error(test_error, error_context, retry=False, fallback=False)
        
        self.assertEqual(report.error_type, "ConnectionError")
        self.assertEqual(report.context.operation, "generate_content")
        self.assertEqual(report.context.component, "expression_analyzer")
        self.assertEqual(report.context.additional_data["max_retries"], 3)
    
    def test_api_route_error_reporting(self):
        """Test that API routes report errors correctly."""
        from langflix.core.error_handler import handle_error, ErrorContext
        
        error_context = ErrorContext(
            operation="process_video_task",
            component="api.routes.jobs",
            additional_data={"job_id": "test-job-123"}
        )
        
        test_error = RuntimeError("Processing failed")
        report = handle_error(test_error, error_context, retry=False, fallback=False)
        
        self.assertEqual(report.error_type, "RuntimeError")
        self.assertEqual(report.context.operation, "process_video_task")
        self.assertEqual(report.context.component, "api.routes.jobs")
        self.assertEqual(report.context.additional_data["job_id"], "test-job-123")
    
    def test_video_editor_error_reporting(self):
        """Test that video_editor reports errors correctly."""
        from langflix.core.error_handler import handle_error, ErrorContext
        
        error_context = ErrorContext(
            operation="create_educational_sequence",
            component="core.video_editor"
        )
        
        test_error = OSError("File not found")
        report = handle_error(test_error, error_context, retry=False, fallback=False)
        
        self.assertEqual(report.error_type, "OSError")
        self.assertEqual(report.context.operation, "create_educational_sequence")
        self.assertEqual(report.context.component, "core.video_editor")
    
    def test_error_severity_determination(self):
        """Test that error severity is determined correctly."""
        handler = ErrorHandler()
        
        # Test critical errors
        context = ErrorContext(operation="test", component="test")
        severity = handler._determine_severity(MemoryError(), context)
        self.assertEqual(severity, ErrorSeverity.CRITICAL)
        
        # Test high severity errors
        severity = handler._determine_severity(ConnectionError(), context)
        self.assertEqual(severity, ErrorSeverity.HIGH)
        
        # Test medium severity errors
        severity = handler._determine_severity(ValueError(), context)
        self.assertEqual(severity, ErrorSeverity.MEDIUM)
    
    def test_error_category_determination(self):
        """Test that error category is determined correctly."""
        handler = ErrorHandler()
        
        context = ErrorContext(operation="test", component="test")
        
        # Test network errors
        category = handler._determine_category(ConnectionError(), context)
        self.assertEqual(category, ErrorCategory.NETWORK)
        
        # Test validation errors
        category = handler._determine_category(ValueError(), context)
        self.assertEqual(category, ErrorCategory.VALIDATION)
        
        # Test resource errors
        category = handler._determine_category(OSError(), context)
        self.assertEqual(category, ErrorCategory.RESOURCE)


if __name__ == '__main__':
    unittest.main()

