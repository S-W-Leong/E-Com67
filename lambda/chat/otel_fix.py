"""
Fix OpenTelemetry StopIteration crash in Lambda.

The crash occurs because entry_points() returns empty in Lambda's environment,
causing next() to raise StopIteration. We fix this by patching entry_points()
to provide a default context entry point when none is found.

This lets OpenTelemetry work normally - we just fix the import crash.
"""
import sys
import importlib.metadata

_original_entry_points = importlib.metadata.entry_points


class _FakeContextEntryPoint:
    """Fake entry point that loads ContextVarsRuntimeContext."""
    name = 'contextvars_context'
    group = 'opentelemetry_context'

    def load(self):
        from opentelemetry.context.contextvars_context import ContextVarsRuntimeContext
        return ContextVarsRuntimeContext


def _patched_entry_points(**kwargs):
    """Wrapper that provides default context entry point if none found."""
    result = _original_entry_points(**kwargs)

    # If looking for opentelemetry_context and got empty result, provide default
    if kwargs.get('group') == 'opentelemetry_context':
        # Handle both old (dict) and new (SelectableGroups) return types
        if hasattr(result, 'select'):
            selected = result.select(name=kwargs.get('name', 'contextvars_context'))
            if not selected:
                return [_FakeContextEntryPoint()]
            return selected
        elif not result or len(list(result)) == 0:
            return [_FakeContextEntryPoint()]

    return result


# Patch before OpenTelemetry imports
importlib.metadata.entry_points = _patched_entry_points
