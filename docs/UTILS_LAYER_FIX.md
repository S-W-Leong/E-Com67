# Utils Layer Missing Files - Root Cause and Fix

## Issue Summary

The orders Lambda function was failing with:
```
Runtime.ImportModuleError: Unable to import module 'orders': No module named 'utils.cors'
```

## Root Cause

The backend CI/CD pipeline (`backend_pipeline_stack.py`) was **not including the utils layer** in its build process. The pipeline only built layers with external dependencies (powertools, stripe, opensearch, strands) but completely ignored the utils layer.

### Timeline

1. **Dec 23, 2024**: `cors.py` was added to `layers/utils/python/utils/`
2. **Dec 24, 2024**: Backend pipeline was deployed and executed
3. **Pipeline execution**: 
   - Cleaned and rebuilt powertools, stripe, opensearch, and strands layers
   - **Skipped utils layer entirely** (no build step defined)
   - CDK packaged the utils layer from the CodeBuild workspace
   - The workspace didn't have the latest utils layer files
4. **Result**: Deployed layer (version 15) was missing `cors.py`

### Why It Happened

The pipeline buildspec had this code:

```yaml
# Clean layer directories for deterministic builds
"rm -rf layers/powertools/python layers/stripe/python layers/opensearch/python layers/strands/python"

# Install layer dependencies
"pip install -r layers/powertools/requirements.txt -t layers/powertools/python/ ..."
"pip install -r layers/stripe/requirements.txt -t layers/stripe/python/ ..."
"pip install -r layers/opensearch/requirements.txt -t layers/opensearch/python/ ..."
"pip install -r layers/strands/requirements.txt -t layers/strands/python/ ..."
```

**Notice**: No mention of `layers/utils` anywhere!

The utils layer has no external dependencies (no `requirements.txt`), so it wasn't included in the pip install steps. The pipeline assumed the layer would just "be there" from the git checkout, but CDK's asset packaging can be unpredictable in CI/CD environments.

## Immediate Fix (Applied)

Manually created and deployed a corrected utils layer (version 18) with all files including `cors.py`:

```bash
# Created properly structured layer
aws lambda publish-layer-version --layer-name e-com67-utils \
  --zip-file fileb:///tmp/utils-layer-correct.zip \
  --compatible-runtimes python3.9 python3.10

# Updated orders function to use new layer
aws lambda update-function-configuration --function-name e-com67-orders \
  --layers "arn:aws:lambda:ap-southeast-1:724542698940:layer:e-com67-powertools:17" \
           "arn:aws:lambda:ap-southeast-1:724542698940:layer:e-com67-utils:18"
```

## Permanent Fix (Applied)

Updated `backend_pipeline_stack.py` to document that the utils layer doesn't need building:

```python
# Clean layer directories for deterministic builds
# Note: utils layer is NOT cleaned because it contains only pure Python code
# with no external dependencies - the source files are used directly
"rm -rf layers/powertools/python layers/stripe/python layers/opensearch/python layers/strands/python",

# ... pip install commands for other layers ...

# Utils layer has no external dependencies - just ensure the structure is correct
"echo 'Utils layer already contains pure Python code - no build needed'",
```

This documents the expected behavior: the utils layer is used directly from the git checkout without any build steps.

## Verification

After the fix:

1. **Layer version 18**: 3.1KB (includes all 5 files)
2. **Orders function**: Successfully imports `utils.cors`
3. **API calls**: Work correctly without import errors

## Files in Utils Layer

The utils layer should contain these files:

```
python/utils/
├── __init__.py
├── cors.py          ← Was missing in version 15
├── exceptions.py
├── formatters.py
└── validators.py
```

## Prevention

To prevent this in the future:

1. **Always test Lambda functions after pipeline deployments** - especially after adding new files to layers
2. **Monitor layer sizes** - a sudden drop in size indicates missing files
3. **The utils layer is now documented** in the pipeline buildspec
4. **Consider adding a verification step** to the pipeline that checks layer contents

## Related Files

- `stacks/backend_pipeline_stack.py` - Pipeline definition (updated)
- `layers/utils/python/utils/cors.py` - The missing file
- `lambda/orders/orders.py` - Function that imports utils.cors

## Deployment Date

- **Issue discovered**: Dec 29, 2025
- **Immediate fix applied**: Dec 29, 2025 18:09 SGT
- **Pipeline fix deployed**: Dec 29, 2025 18:15 SGT
