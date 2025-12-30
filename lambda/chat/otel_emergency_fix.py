"""
Emergency OpenTelemetry fix for Lambda environments.

This module provides a comprehensive fix for the OpenTelemetry StopIteration error
that occurs in Lambda environments when multiple layers provide OpenTelemetry packages.

This fix is embedded directly in the Lambda function to ensure it's always available.
"""

import os
import sys

def apply_emergency_otel_fix():
    """
    Apply emergency OpenTelemetry fix to prevent StopIteration error.
    
    This function must be called BEFORE any other imports that might use OpenTelemetry.
    """
    
    # Set environment variables to disable OpenTelemetry
    os.environ['OTEL_SDK_DISABLED'] = 'true'
    os.environ['OTEL_PYTHON_DISABLED_INSTRUMENTATIONS'] = 'all'
    os.environ['OTEL_PYTHON_CONTEXT'] = 'contextvars_context'
    
    print("EMERGENCY: OpenTelemetry environment variables set", file=sys.stderr)
    
    try:
        # Method 1: Patch existing OpenTelemetry context module if already imported
        if 'opentelemetry.context' in sys.modules:
            otel_context = sys.modules['opentelemetry.context']
            if hasattr(otel_context, '_load_runtime_context'):
                def safe_load_runtime_context():
                    """Safe replacement that never raises StopIteration"""
                    import contextvars
                    
                    class SafeRuntimeContext:
                        def __init__(self):
                            self._context_var = contextvars.ContextVar('otel_context', default={})
                        
                        def attach(self, context):
                            return self._context_var.set(context)
                        
                        def detach(self, token):
                            self._context_var.reset(token)
                        
                        def get_current(self):
                            return self._context_var.get()
                    
                    return SafeRuntimeContext()
                
                otel_context._load_runtime_context = safe_load_runtime_context
                print("EMERGENCY: Patched existing OpenTelemetry context module", file=sys.stderr)
        
        # Method 2: Try to import and patch OpenTelemetry directly
        try:
            import opentelemetry.context
            if hasattr(opentelemetry.context, '_load_runtime_context'):
                def safe_load_runtime_context():
                    """Safe replacement that never raises StopIteration"""
                    import contextvars
                    
                    class SafeRuntimeContext:
                        def __init__(self):
                            self._context_var = contextvars.ContextVar('otel_context', default={})
                        
                        def attach(self, context):
                            return self._context_var.set(context)
                        
                        def detach(self, token):
                            self._context_var.reset(token)
                        
                        def get_current(self):
                            return self._context_var.get()
                    
                    return SafeRuntimeContext()
                
                opentelemetry.context._load_runtime_context = safe_load_runtime_context
                print("EMERGENCY: Patched OpenTelemetry context via direct import", file=sys.stderr)
        except ImportError:
            print("EMERGENCY: OpenTelemetry not available for direct patching", file=sys.stderr)
        
        # Method 3: Set up import hook to catch future OpenTelemetry imports
        original_import = __builtins__.get('__import__', __import__)
        
        def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
            """Patched import that fixes OpenTelemetry context loading"""
            try:
                module = original_import(name, globals, locals, fromlist, level)
                
                # Patch opentelemetry.context when it's imported
                if name == 'opentelemetry.context' or (fromlist and 'context' in fromlist and name.startswith('opentelemetry')):
                    try:
                        if hasattr(module, '_load_runtime_context'):
                            def safe_load_runtime_context():
                                """Safe replacement that never raises StopIteration"""
                                import contextvars
                                
                                class SafeRuntimeContext:
                                    def __init__(self):
                                        self._context_var = contextvars.ContextVar('otel_context', default={})
                                    
                                    def attach(self, context):
                                        return self._context_var.set(context)
                                    
                                    def detach(self, token):
                                        self._context_var.reset(token)
                                    
                                    def get_current(self):
                                        return self._context_var.get()
                                
                                return SafeRuntimeContext()
                            
                            module._load_runtime_context = safe_load_runtime_context
                            print(f"EMERGENCY: Patched OpenTelemetry context during import of {name}", file=sys.stderr)
                    except Exception as e:
                        print(f"EMERGENCY: Failed to patch OpenTelemetry during import: {e}", file=sys.stderr)
                
                return module
            except Exception as e:
                print(f"EMERGENCY: Import error for {name}: {e}", file=sys.stderr)
                raise
        
        # Apply the import hook
        if isinstance(__builtins__, dict):
            __builtins__['__import__'] = patched_import
        else:
            __builtins__.__import__ = patched_import
        
        print("EMERGENCY: OpenTelemetry import hook installed", file=sys.stderr)
        
        # Method 4: Nuclear option - completely replace OpenTelemetry modules
        if os.environ.get('OTEL_BYPASS_ENABLED', 'false').lower() == 'true':
            _apply_nuclear_bypass()
        
    except Exception as e:
        print(f"EMERGENCY: Failed to apply OpenTelemetry fix: {e}", file=sys.stderr)
        # Don't raise the exception - we want the Lambda to continue running

def _apply_nuclear_bypass():
    """Nuclear option: completely replace OpenTelemetry with no-op implementations"""
    try:
        # Create no-op implementations
        class NoOpTracer:
            def start_span(self, *args, **kwargs):
                return NoOpSpan()
            
            def start_as_current_span(self, *args, **kwargs):
                return NoOpSpan()
        
        class NoOpSpan:
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
            
            def set_attribute(self, *args, **kwargs):
                pass
            
            def set_status(self, *args, **kwargs):
                pass
            
            def record_exception(self, *args, **kwargs):
                pass
            
            def end(self, *args, **kwargs):
                pass
        
        class NoOpMeter:
            def create_counter(self, *args, **kwargs):
                return NoOpInstrument()
            
            def create_histogram(self, *args, **kwargs):
                return NoOpInstrument()
            
            def create_gauge(self, *args, **kwargs):
                return NoOpInstrument()
        
        class NoOpInstrument:
            def add(self, *args, **kwargs):
                pass
            
            def record(self, *args, **kwargs):
                pass
        
        class NoOpContext:
            def attach(self, *args, **kwargs):
                return None
            
            def detach(self, *args, **kwargs):
                pass
            
            def get_current(self, *args, **kwargs):
                return {}
        
        # Create mock modules
        def create_mock_module(name):
            mock_module = type(sys)('mock_' + name.replace('.', '_'))
            mock_module.__file__ = f'<mock {name}>'
            mock_module.__package__ = name.rsplit('.', 1)[0] if '.' in name else ''
            return mock_module
        
        # Mock the main OpenTelemetry modules
        otel_modules = [
            'opentelemetry',
            'opentelemetry.trace',
            'opentelemetry.metrics', 
            'opentelemetry.context',
            'opentelemetry.sdk',
            'opentelemetry.instrumentation'
        ]
        
        for module_name in otel_modules:
            if module_name not in sys.modules:
                mock_module = create_mock_module(module_name)
                sys.modules[module_name] = mock_module
        
        # Set up the context module with safe _load_runtime_context
        context_module = sys.modules['opentelemetry.context']
        context_module.attach = lambda *args, **kwargs: None
        context_module.detach = lambda *args, **kwargs: None
        context_module.get_current = lambda: {}
        
        def safe_load_runtime_context():
            """Safe context loader that never raises StopIteration"""
            return NoOpContext()
        
        context_module._load_runtime_context = safe_load_runtime_context
        
        # Set up the trace module
        trace_module = sys.modules['opentelemetry.trace']
        trace_module.get_tracer = lambda *args, **kwargs: NoOpTracer()
        trace_module.set_tracer_provider = lambda *args, **kwargs: None
        
        # Set up the metrics module
        metrics_module = sys.modules['opentelemetry.metrics']
        metrics_module.get_meter = lambda *args, **kwargs: NoOpMeter()
        metrics_module.set_meter_provider = lambda *args, **kwargs: None
        
        print("EMERGENCY: Nuclear OpenTelemetry bypass applied", file=sys.stderr)
        
    except Exception as e:
        print(f"EMERGENCY: Failed to apply nuclear bypass: {e}", file=sys.stderr)

# Auto-apply the fix when this module is imported
apply_emergency_otel_fix()