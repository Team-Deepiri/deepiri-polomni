# Hierarchical Sky Search

Coarse-to-fine search for the preferred RBLE scar axis on large HEALPix maps.

## Algorithm

1. **Coarse pass** — downsample to NSIDE 16 (configurable), scan 12 axis candidates
2. **Refine** — sample axes within a 15° cone around the coarse winner at full resolution
3. **Score** — return `DetectionReport` with search metadata in `metadata`

## CLI

```bash
poetry run polomni scan --real --hierarchical --nside 128
```

## Python

```python
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search

report = hierarchical_sky_search(cmb_map, coarse_nside=16, refine_cone_deg=15)
print(report.metadata["axis_shift_deg"])
```

See [FALSIFICATION_CRITERIA.md](../theory/FALSIFICATION_CRITERIA.md) for Bonferroni correction guidance on multi-test searches.
