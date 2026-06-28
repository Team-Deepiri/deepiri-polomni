# RBLE Math Proof & Multiverse Studio — Master Plan

**Goal:** Close the loop from theory → numerical proof (notebooks) → `polomni.math` provers → REST/CLI → **Multiverse Studio** UI for novel scientist-facing visualizations.

---

## Math inventory (from original RBLE design)

| ID | Equation | Theory doc | Code module | Notebook (existing) | Proof status |
|----|----------|------------|-------------|---------------------|--------------|
| **VP** | Master action \(\mathcal{S}_{\text{RBLE}}\) | VARIATIONAL_PRINCIPLE.md | (new) `math/variational.py` | **09** (new) | Gap |
| **Eq1** | Informational-string Einstein | RBLE_MASTER §1 | `gravity/field_equations.py` | 01 (partial) | Partial |
| **Eq2** | Radon-rotated FP compact | §2 | `inflation/fokker_planck.py` | 04 | Exists |
| **Eq3** | WDW bifurcation closure | §3 | `superspace/wdw_generator.py` | 03 | Exists |
| **Eq4** | Choice entropy continuity | §4 | `conservation.py` | 01, 06 | Exists |
| **Eq5** | Radon-modulated FP full | §5 | `inflation/drift_diffusion.py` | 04 | Partial |
| **Eq6** | Spherical Radon scar \(S^2\) | §6 | `radon/transform_s2.py` | 05 | Exists |
| **Eq7** | ER=EPR conductance | §7 | `conductance/bridge_tensor.py` | 06 | Exists |
| **Eq8** | Kähler stabilization | §8 | `landscape/kahler.py` | (gap) | Gap |
| **P1–P3** | Falsification trinity | FALSIFICATION_CRITERIA.md | observatory + conductance | **10** (new) | Gap |
| **Loop** | Full multiverse cycle | SYSTEM_OVERVIEW | `integration/workflow.py` | **11** (new) | Partial |

---

## Deliverables by agent

### Agent 1 — `polomni.math` proof engine
**Owns:** `src/polomni/math/`, `tests/math/`, `polomni math prove` CLI

- `proofs/base.py` — `ProofResult`, `MathProofSuite`
- `proofs/eq01_gravity.py` … `eq08_kahler.py` — numerical checks vs theory tolerances
- `proofs/variational.py` — Lagrangian term positivity, closure identity
- `proofs/falsification.py` — P1 injection recovery, P2 directed diffusion, P3 conductance phase
- `prove_all()` → JSON report; exit code 1 if any critical proof fails

### Agent 2 — Notebooks 09–11 (theory proofs)
**Owns:** `experiments/09_*.ipynb`, `10_*.ipynb`, `11_*.ipynb`

Each notebook: theory markdown → sympy where useful → call `polomni.math` + core modules → assert cells with printed PASS/FAIL → publication figures.

- **09** Variational principle & equation chain overview
- **10** Falsification trinity (P1 scar, P2 \(f_{\mathrm{NL}}\) proxy, P3 GW phase)
- **11** Integrated multiverse loop (district → stream → WDW → CMB score)

### Agent 3 — Notebooks 12–13 + math API
**Owns:** `experiments/12_*.ipynb`, `13_*.ipynb`, `src/polomni/api/routers/math.py`

- **12** Kähler landscape & string coupling (Eq 8 + STRING_LANDSCAPE_COUPLING)
- **13** Real-data theory bridge (Planck \(C_\ell\) + RBLE score on WMAP)
- API: `GET /math/proofs`, `POST /math/prove`, `GET /math/equations`

### Agent 4 — Multiverse Studio backend
**Owns:** `src/polomni/studio/`, `src/polomni/api/routers/studio.py`, `src/polomni/viz/multiverse/`

Data providers:
- `district_graph_3d()` — nodes/edges for force graph
- `landscape_surface()` — Kähler potential grid
- `scar_sphere()` — HEALPix → lat/lon/value for globe
- `stream_flux_series()` — vacuum pipeline stages
- `branch_simplex()` — N-way choice weights
- `falsification_panel()` — P1/P2/P3 flags from latest proof + report

### Agent 5 — Multiverse Studio UI + wiring
**Owns:** `src/polomni/studio/static/studio.html`, `studio.js`, `studio.css`, CLI `polomni studio`, docs

- Single-page app at `/studio` (no CDN — inline Plotly-lite or canvas/WebGL)
- Panels: Multiverse Graph | Landscape | Scar Sphere | Stream Flux | Branch Simplex | Proofs | Falsification
- Wire to `/studio/*` API; link from dashboard; `polomni studio` opens browser
- Update README, `docs/guides/multiverse_studio.md`, CHANGELOG

---

## Integration checklist (parent agent)

- [ ] `main.py` / `app.py` mount studio + math routers
- [ ] `make prove` target
- [ ] CI: `polomni math prove` in smoke workflow
- [ ] All notebooks execute top-to-bottom (nbconvert smoke optional)
- [ ] 120+ tests passing
- [ ] Commit + push `dev` + `main`

---

## UI vision (Multiverse Studio)

```
┌─────────────────────────────────────────────────────────────┐
│  POLOMNI MULTIVERSE STUDIO                    [Run Proofs]  │
├──────────────┬──────────────┬──────────────────────────────┤
│ 3D District  │ Kähler       │  Scar Sphere (HEALPix)       │
│ Graph        │ Landscape    │  + preferred axis vector     │
├──────────────┴──────────────┴──────────────────────────────┤
│ Stream Flux Animation    │ Branch Simplex │ P1 P2 P3 lamps  │
└─────────────────────────────────────────────────────────────┘
```

Novel for scientists: **simultaneous** district topology + landscape geometry + sky scar axis + falsification status — not available in CAMB/CLASS/healpy alone.
