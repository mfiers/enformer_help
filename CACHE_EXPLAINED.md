# Cache Behavior Explained

## Summary

✅ **The cache IS working correctly!** Both scripts properly detect and use cached Enformer results.

## How Caching Works

### Two-Level Cache Checking

1. **enformer_help internal caching** (always active)
   - `run_enformer_keep_in_memory()` checks cache internally
   - If sequence is cached: loads from disk (fast ~0.1-1 sec)
   - If not cached: runs model (slow ~5-10 sec)

2. **Script-level cache checking** (when using `--resume` flag)
   - Checks cache BEFORE calling `run_enformer_keep_in_memory()`
   - If cached: skips function call entirely
   - Provides better progress statistics

### Current Cache Status

You already have **13,572+ cached results** (~295 GB)!

Location: `/data/teachers/software/enformer_help/cache/enformer/`

## Cache Detection Logic

### Verified Working ✓

```python
# Both paths resolve to the same location
enformer_help cache: /data/teachers/software/enformer_help/cache/enformer
script cache:        /data/teachers/software/enformer_help/cache/enformer
Paths match: True ✓
```

### How It Works

1. **Sequence hashing**:
   ```python
   sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
   ```

2. **Cache file naming**:
   ```python
   cache_file = cache_folder / f"{sha}.pkl.gz"
   ```

3. **Existence check**:
   ```python
   return cache_file.exists()
   ```

## What the --resume Flag Actually Does

### WITHOUT --resume (default)

```
For each SNP:
  1. Retrieve sequences (parallel)
  2. Call run_enformer_keep_in_memory(fseq)
     → Checks cache internally
     → If cached: load from disk (0.1-1 sec)
     → If not: run model (5-10 sec)
  3. Call run_enformer_keep_in_memory(nseq)
     → Same logic
  4. Count as "computed" (even if loaded from cache)
```

**Result**: Fast for cached (loads), slow for uncached (computes)

### WITH --resume

```
For each SNP:
  1. Retrieve sequences (parallel)
  2. Check if BOTH sequences are cached
     → If yes: skip entirely, count as "cached"
     → If no: continue to step 3
  3. Call run_enformer_keep_in_memory(fseq)
     → Checks cache internally
     → If cached: load from disk
     → If not: run model
  4. Call run_enformer_keep_in_memory(nseq)
     → Same logic
  5. Count as "cached" or "computed" appropriately
```

**Result**: Same speed, but better statistics tracking

## Improved Statistics

The scripts now track:

- **computed**: Sequences that needed model execution (new results)
- **cached**: Sequences loaded from cache (already computed)
- **failed**: Sequences that couldn't be processed

### Progress Bar Format

```
Processing:  45%|████████     | 450/1000 [05:23<06:45, 1.35SNP/s] computed=125 cached=300 failed=25
```

Where:
- **computed**: Actually ran Enformer model (slow)
- **cached**: Loaded from existing cache (fast)
- **failed**: Sequence retrieval or processing error

## Performance Impact

### Cache Hit (sequence already computed)

- **With --resume**: ~0.001 sec (skips function call)
- **Without --resume**: ~0.1-1 sec (loads from cache internally)

**Difference**: Negligible (milliseconds)

### Cache Miss (needs computation)

- **With or without --resume**: ~5-10 sec (must run model)

**Difference**: None

## Recommendation

### For Normal Use

```bash
# Simple - let enformer_help handle caching
python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 10000
```

- Cache is used automatically
- All results properly cached for future runs
- Shows total progress

### For Better Statistics

```bash
# With --resume for clearer progress tracking
python batch_enformer.py Kunkle_etal_Stage1_results.txt -n 10000 --resume
```

- Cache is used automatically
- Shows separate "computed" vs "cached" counts
- Useful for understanding what's actually happening

### For Long-Running Jobs

```bash
# Run in screen/tmux with resume for restartability
screen -S enformer
python batch_enformer.py Kunkle_etal_Stage1_results.txt --resume

# If interrupted, restart with:
python batch_enformer.py Kunkle_etal_Stage1_results.txt --resume
# (already-cached results will be skipped automatically)
```

## Verification

Run the cache verification script to check your current status:

```bash
python verify_cache.py
```

Expected output:
```
Cache folder exists: ✓
Total cached files: 13,572+
Paths match: True ✓
```

## Cache Management

### View Cache Size

```bash
du -sh cache/enformer
# Example: 295G cache/enformer
```

### Count Cached Files

```bash
ls cache/enformer/*.pkl.gz | wc -l
# Example: 13572
```

### Check Specific Sequence

```python
import hashlib
from pathlib import Path

sequence = "ACGT..." * 49152  # your 196,608 bp sequence
sha = hashlib.sha256(sequence.encode('utf-8')).hexdigest()
cache_file = Path("cache/enformer") / f"{sha}.pkl.gz"
print(f"Cached: {cache_file.exists()}")
```

### Clear Cache (if needed)

```bash
# ⚠️ WARNING: This deletes all cached results!
rm -rf cache/enformer/*.pkl.gz
```

## Conclusion

✅ Cache detection is working correctly
✅ Both scripts use the same cache location
✅ enformer_help handles caching internally
✅ --resume flag is optional (mainly for better statistics)
✅ You already have 13,572+ cached results saving you days of compute time!

**Bottom line**: Just run the scripts. The caching works automatically and correctly. Use `--resume` if you want clearer progress statistics about what's cached vs newly computed.
