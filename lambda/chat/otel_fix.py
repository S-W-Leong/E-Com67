"""
Disable OpenTelemetry for Lambda - we use Powertools for tracing instead.

Strands SDK imports opentelemetry at module level, which crashes in Lambda
due to a StopIteration bug. Since we don't need OTEL, we stub it out entirely.
"""
import sys
import types


class _NoOpSpan:
    """No-op span that does nothing."""
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def set_attribute(self, *a, **kw): pass
    def set_status(self, *a, **kw): pass
    def add_event(self, *a, **kw): pass
    def record_exception(self, *a, **kw): pass
    def end(self, *a, **kw): pass
    def is_recording(self): return False
    @property
    def context(self): return None


class _NoOpTracer:
    """No-op tracer that returns no-op spans."""
    def start_span(self, *a, **kw): return _NoOpSpan()
    def start_as_current_span(self, *a, **kw): return _NoOpSpan()


class _NoOpTracerProvider:
    """No-op tracer provider."""
    def get_tracer(self, *a, **kw): return _NoOpTracer()


# Stub out opentelemetry modules
def _create_module(name):
    mod = types.ModuleType(name)
    mod.__file__ = f'<stub {name}>'
    return mod

# Create module hierarchy
_otel = _create_module('opentelemetry')
_otel_trace = _create_module('opentelemetry.trace')
_otel_context = _create_module('opentelemetry.context')

# Populate trace module
_otel_trace.get_tracer = lambda *a, **kw: _NoOpTracer()
_otel_trace.get_tracer_provider = lambda: _NoOpTracerProvider()
_otel_trace.set_tracer_provider = lambda *a, **kw: None
_otel_trace.INVALID_SPAN = _NoOpSpan()
_otel_trace.INVALID_SPAN_CONTEXT = None
_otel_trace.Span = _NoOpSpan
_otel_trace.Tracer = _NoOpTracer
_otel_trace.TracerProvider = _NoOpTracerProvider

# Populate context module (prevents StopIteration crash)
_otel_context._RUNTIME_CONTEXT = None
_otel_context.attach = lambda ctx: None
_otel_context.detach = lambda token: None
_otel_context.get_current = lambda: {}
_otel_context.set_value = lambda key, val, ctx=None: {}
_otel_context.get_value = lambda key, ctx=None: None

# Register in sys.modules
sys.modules['opentelemetry'] = _otel
sys.modules['opentelemetry.trace'] = _otel_trace
sys.modules['opentelemetry.context'] = _otel_context
_otel.trace = _otel_trace
_otel.context = _otel_context
