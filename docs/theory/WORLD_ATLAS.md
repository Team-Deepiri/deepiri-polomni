# World Atlas — RBLE scan over the NASA Exoplanet Archive

**Status:** applied-mathematics note + live observatory feature (not a claim of new physics)
**Data:** NASA Exoplanet Archive planetary-systems table (`nasa_exoplanet_ps`, `polomni data fetch`)
**Code:** `src/polomni/observatory/pipeline/sources/exoplanets.py`, `src/polomni/viz/cosmos/worlds.py`
**Routes/CLI:** `GET /cosmos/worlds`, `polomni data worlds`

---

## System (plain language)

The NASA Exoplanet Archive lists every *confirmed* planet outside the Solar System —
6,333 as of 2026 — each with a real position on the sky (right ascension, declination).
A "world atlas" asks a single question:

> Is the distribution of worlds on the sky ordered around a preferred axis, the way the
> RBLE multiverse picture predicts scars should be — and, if so, is that order real
> physics or just an artifact of how we look?

There are three sub-systems tangled together, and untangling them is the whole problem:

1. **The worlds themselves** — where each confirmed planet actually points.
2. **The survey footprint** — the telescope fields that happened to look there
   (Kepler stared at one patch of sky; TESS scans bands; microlensing follows the
   Galactic bulge).
3. **The Milky Way** — a disk of stars whose plane is a natural axis in the sky.

A naive scan cannot tell these apart. This note builds the scan so it can.

## Inventory

| Entity | What it is | Measurables |
|---|---|---|
| World | A confirmed exoplanet | RA (deg), Dec (deg), period (d), radius (R⊕), mass (M♃), host T_eff (K), disc. year, method |
| Host star | Star the world orbits | position, T_eff |
| Survey footprint | Set of sky pixels that were observed | the occupied HEALPix mask |
| Galactic plane | Milky Way disk reference | Galactic pole unit vector (equatorial) |

Measurable quantities with units: positions (deg), counts (dimensionless), angular
separation (deg), order parameters (dimensionless).

## Observations (grounded in the real 6,333-row catalog)

- Worlds occupy **only 5.4% of the sky** at NSIDE 64, 17.8% at NSIDE 32 — a heavily
  footprint-dominated distribution.
- Discovery methods dominate asymmetrically: **Transit 4,674, Radial Velocity 1,196,
  Microlensing 282, Imaging 98**, + 7 minor methods.
- Alignment-order parameter S (see below) by method:

| Method | N | S | axis ↔ Galactic pole |
|---|---|---|---|
| All worlds | 6,333 | 0.425 | 16.6° |
| Transit | 4,674 | 0.581 | 78° |
| Radial Velocity | 1,196 | **0.058** | 53° |
| Microlensing | 282 | **0.980** | **88°** |
| Imaging | 98 | 0.278 | 71° |

**Reading the table:** the sky-complete method (Radial Velocity) is nearly *isotropic*.
The most-ordered method (Microlensing) is ordered *in the Galactic plane* — its axis is
88° from the pole, i.e. pointing at the bulge. The full-sample anisotropy is therefore a
mixture of Kepler-field footprint (Transit) and Galactic-plane crowding (Microlensing).
This is the selection-bias statement the whole design exists to make.

## Candidate invariants

- **Tr(Q) ≡ 1 exactly**, for any subset, any NSIDE, any weight. Q = ⟨n nᵀ⟩ over world
  unit vectors; the trace of the outer-product mean is the mean of unit traces.
  Verified numerically to 1e-15 across all method subsets. Used as the test that the
  tensor is well-formed in the API (`Tr(Q) invariant`).
- **Q symmetric** ⇒ real eigenvalues, always diagonalizable (no fudge required).
- **λ₁ ≥ 1/3** always (Rayleigh quotient of a PSD matrix against any direction ≥ 0;
  with the constraint λ₁ ≥ λ₂ ≥ λ₃, trace 1 ⇒ λ₁ ≥ 1/3). Isotropy is λ = (1/3, 1/3, 1/3).
  The scalar `S = (3λ₁ − 1)/2` runs 0 (isotropic) → 1 (perfectly aligned).

## Dimensionless groups

Everything is already dimensionless (unit vectors, order parameters, separations in deg).
The only free parameter is the scan NSIDE (a resolution choice, not a physical one) and
the density weight (`count` / `teff` / `period` — which physical quantity is stacked into
the HEALPix bins). The RBLE score S_RBLE is the existing dimensionless scar integral.

## Candidate state variables

- **The occupancy mask** is the state variable that restores the Markov property to the
  null problem: "which pixels *can* be occupied" is the full survey-footprint summary.
- **Per-method preferred axis** is the state variable that separates footprint physics
  from true physics — each method has a different mask, so axis *agreement* across methods
  is the only thing that can survive selection.

## The null model — footprint-matched permutation

An isotropic null is **not** reachable for this system: the survey mask already breaks
isotropy, so comparing against a uniform sphere would condemn the footprint, not the
physics. The honest null is:

1. Fix the observed occupancy mask (which pixels are occupied).
2. Permute the per-pixel world counts **within** the mask.
3. Score each permuted map at the **observed** preferred axis (single geodesic integral,
   ~30 ms/map ⇒ 40-ensemble null in ~1.2 s).
4. Report σ = (S_obs − μ_null) / σ_null.

Current result: S_RBLE = 0.44 vs null μ=0.24 σ=0.013 → **+15.5σ**. This says the world
density is strongly ordered at the found axis even against random reshuffling in the
mask — but it does **not** by itself distinguish Galactic-plane crowding from true
beyond-Milky-Way order. That job belongs to the method audit.

## The dipole test — cosmic-rest-frame alignment

A physical world anisotropy must point at a *cosmic rest frame*; a survey artifact
points at the survey. The dipole of the world-direction set,

$$\hat D = \frac{\langle n\rangle}{|\langle n\rangle|}, \quad |\langle n\rangle| = |\frac{1}{N}\sum_i n_i| \in [0,1],$$

is the first spherical-harmonic moment of the distribution. We measure its angular
separation from four named references:

| Reference | Direction (J2000) | Meaning |
|---|---|---|
| **CMB dipole apex** | RA 167.942°, Dec −6.944° | Solar System's motion through the CMB rest frame (Planck 2018) — the one direction a *physical* anisotropy must point at |
| Ecliptic north pole | RA 270°, Dec 66.56° | Solar-system plane reference |
| Galactic north pole | RA 192.8595°, Dec 27.1283° | Milky Way disk normal |
| Kepler field center | RA 290.5°, Dec 44.5° | The dominant transit survey footprint |

**Current result (real 6,333 worlds):** dipole |⟨n⟩| = 0.422 with a 68% bootstrap cone of
1.1°, sitting **4.8° from the Kepler field center** and ≥ 62° from the CMB dipole apex
and Galactic pole for *every* discovery method. The cosmic-rest-frame test is therefore
**negative**: the only significant world dipole is the survey footprint, and no sample
leans toward the CMB rest frame.

**Robustness — multiplicity:** planets in the same system share one sky position and are
not independent. Resampling per *host* (each system's planets drawn together; 4,747
systems) leaves the result essentially unchanged: dipole 0.407, still 6.4° from the
Kepler field, 68% cone 1.3° vs 1.1° per-world. Multiplicity is not manufacturing the
signal.

**Robustness — Kepler excision (the decisive test):** a *physical* scar must survive
removing the survey field it points at. Excising worlds near the Kepler field center:

| Cut radius | N left | \|⟨n⟩\| | isotropic expectation | ↔ Kepler |
|---|---|---|---|---|
| full | 6,333 | 0.422 | 0.007 | 4.8° |
| >5° | 4,844 | 0.250 | 0.008 | 10.6° |
| **>8°** | **3,498** | **0.075** | **0.010** | **60.3°** |
| >12° | 3,443 | 0.078 | 0.010 | 58.5° |
| >20° | 3,313 | 0.081 | 0.010 | 58.6° |

At >8° the dipole collapses to 0.075 — **7.5× the isotropic shot-noise expectation, and
no longer pointed at Kepler** (60° away). The full-sample dipole was the Kepler
footprint; what survives excision is a small residual that does not point at any cosmic
reference and is far from a scar claim. This is the strongest evidence in the atlas that
**no axis-aligned world order exists beyond the survey footprint.**

Per-method dipoles (bootstrap 68% cone):

| Method | N | \|⟨n⟩\| | 68% cone | ↔ Kepler | ↔ CMB apex |
|---|---|---|---|---|---|
| Transit | 4,674 | 0.561 | 0.8° | **2.4°** | 63.4° |
| Microlensing | 282 | 0.983 | 0.4° | 76.5° | 84.2° |
| Radial Velocity | 1,196 | 0.042 | 30.6° | 18.3° | 62.7° |
| Imaging | 98 | 0.242 | 19.9° | 52.0° | 77.8° |

RV — the sky-complete method — has a dipole consistent with zero (|⟨n⟩|=0.042). The
tight cones (Transit, Microlensing) are exactly the footprint-dominated samples.

## The world-sky power spectrum — a novel observable

No published angular power spectrum exists for the *confirmed-planet* sky, so this is a
genuinely new measurement. We compute pseudo-C_ℓ via HEALPix `anafast` on the NSIDE-32
density map, with a **uniform-within-footprint** null: each null map keeps the observed
occupancy mask fixed but reassigns every world to a uniformly random occupied pixel,
destroying all spatial structure while preserving the footprint. This is the correct
null for the same reason as above — isotropic sky is unreachable.

**Current result:** the observed C_ℓ is consistent with random placement within the
footprint at every multipole **except ℓ=1**, which shows ~6.5σ excess (p < 0.001) — and
ℓ=1 is exactly the dipole, i.e. the Kepler-field footprint. Multipoles ℓ=2..12 are
within the 16–84% null band (no statistically significant excess), and high-ℓ is
slightly *below* the null (smooth, not clumpy). Summary: **no world scar survives at any
multipole beyond the survey footprint.**

Caveats shipped with the result: (a) the low-ℓ band is dominated by the fixed mask, so
small ℓ deviations are footprint statements by construction; (b) the `masked` field
divides by the window power (order-0 MASTER), which is unstable below the footprint's
angular resolution and is flagged as such; (c) the null is uniform-within-footprint, not
a model of detector-level selection within the field.

## The cross-sky test — independent skies must agree

The sharpest falsifier of a *world* scar: if the axis is a property of the universe
(multiverse coupling, preferred frame), every independent sky must point at it. Each
catalog we hold has its own survey footprint and its own selection physics, so their
dipoles should *coincide* under the scar hypothesis and *differ* under the footprint
hypothesis. The tool (`polomni data cross-sky`, `GET /cosmos/cross-sky`) loads every
cached independent sky, computes each sky's dipole, and reports the pairwise axis
separations.

| Sky | N | \|⟨n⟩\| | iso expect | ↔ CMB apex | ↔ Kepler |
|-----|---|--------|-----------|-----------|---------|
| exoplanets | 6,333 | 0.422 | 0.007 | 63.6° | 4.8° |
| SDSS galaxies | 80 | 0.423 | 0.065 | 87.2° | 67.8° |

**Pairwise axis separation: exoplanets ↔ SDSS galaxies = 71.9°.**

The two genuinely independent skies disagree by nearly a right angle. A scar locked to
one preferred axis must appear in *both* — it does not. Each dipole instead points at
its own survey footprint: exoplanets at the Kepler field (4.8°), SDSS galaxies at the
northern galactic cap the survey observes (|b|>~50°, the origin of its 0.423 dipole vs
0.065 isotropic expectation — the footprint speaking again).

Gravitational-wave events were **excluded from this comparison, not ignored**: the GWTC
`network_axis` is the interferometer network's antenna-pattern geometry (5 unique
directions across 100 events), not a sky direction, and `load_gw_vectors` now raises if
fewer than half the directions are unique rather than shipping detector geometry as
astronomy. The Planck SMICA CMB map was also attempted as a third sky; after masking
|b|≤20° and removing the dipole the low-ℓ axes are the mask boundary, not a world
signal.

**Conclusion (honest null):** the cross-sky test *falsifies* a common world axis. The
exoplanet dipole is the Kepler footprint; the SDSS dipole is the northern-cap footprint.
No independent sky confirms the other's axis.

## The bubble-collision search — the falsifiable multiverse observable

The one multiverse signature with a concrete, observable prediction is a **bubble
collision**: in eternal inflation our bubble can collide with another bubble of
different vacuum energy, and the collision leaves a **circular temperature edge** in the
CMB — a step in temperature across the boundary of the collided region (Kleban 2011;
Aguirre, Johnson & Larfors; Feeney et al. 2011 "First observational tests of eternal
inflation" searched for exactly these circles and found none in WMAP).

`polomni data bubble` (`GET /cosmos/bubble-search`) is a search instrument for this
signature:

1. **Edge statistic** — for every candidate circle (grid of centers × radii), the edge
   amplitude is `⟨T⟩ just outside − ⟨T⟩ just inside` the boundary, in µK.
2. **Honest null** — C_ℓ-matched Gaussian realizations (true large-scale correlation
   structure preserved) with the **same Galactic mask and same geometry**, and the
   **look-elsewhere correction**: the p-value asks how often the *strongest circle in a
   null realization* beats the observed strongest circle.
3. **Injection gate** — a synthetic step (a planted collision) is recovered **exactly**
   (same center, same radius) by the scan, proving the instrument can find a real
   collision if one is there.
4. **Step check** — a collision is a *step* (flat inside, flat outside, one sharp edge).
   The radial profile of the strongest circle is shipped so a smooth large-scale
   gradient cannot masquerade as a bubble.

**Current result on real Planck SMICA:** strongest edge 35.9 µK vs null median 34.6 µK,
**p = 0.35 — no statistically significant circular temperature edge**. The strongest
circle's radial profile is a smooth gradient, not a step. This is consistent with the
published null result (Feeney et al. 2011). The instrument is the deliverable: a
falsifiable, injection-validated search for the one observable eternal inflation
predicts, run on real sky data.

## Adversarial validation (symmetry broken)

- **Method split:** the full-sample axis does **not** persist across methods with different
  footprints — Transit and Microlensing disagree strongly with sky-complete Radial
  Velocity (S≈0). A genuine scar would survive the split.
- **Galactic-pole reference:** Microlensing is *in-plane* (88°) — its order is the Milky
  Way, not the multiverse. The tool reports the separation from the pole for the full
  sample and every method, so a user cannot mistake disk physics for a world scar.
- **Weight sweep:** the payload can re-run with `weight=teff|period`; the null is
  regenerated for each weight, so no weighting can hide the footprint.

## Proof strategy (what we assert vs what we conjecture)

- **Asserted (verified numerically):** Tr(Q)=1 invariant; S ∈ [0,1]; null permutation
  preserves the mask exactly; fixed-axis null scores are cheap; the dipole bootstrap
  cone is a finite-sample error budget; the world C_ℓ has a well-defined
  uniform-within-footprint null; per-host resampling leaves the dipole conclusion
  unchanged; Kepler excision collapses the dipole toward the isotropic expectation;
  the cross-sky test falsifies a common world axis (independent skies disagree by
  71.9°); GW `network_axis` is detector geometry and is rejected rather than shipped
  as a sky direction; the bubble-collision search recovers planted collision steps
  exactly (injection gate) and finds no significant circular edge in real Planck
  SMICA (p≈0.35 vs the C_ℓ- and mask-matched null).
- **Conjecture (labeled as such):** the world distribution contains axis-aligned order
  *beyond* survey footprint and Milky Way structure. The current evidence *rejects* this
  conjecture for the full sample (RV ≈ isotropic; dipole = Kepler footprint, collapsing
  to ~shot noise on excision; C_ℓ = null except the footprint dipole at ℓ=1). The
  machinery is built so a future dataset — e.g. a sky-complete transit survey — can
  re-run the exact same nulls.

## Domain of validity

- The significance is against **footprint-matched permutation**, not against unknown
  survey selection. It cannot see a selection effect that permuting within the mask
  preserves (e.g. a radial gradient within the Kepler field).
- The catalog is detection-limited: fainter worlds exist where telescopes didn't look.
  "Isotropic RV sample" is the best-available proxy for a sky-complete sample, not a
  guarantee.
- The axis audit is per *discovery method*, not per *instrument*. A single instrument
  used by two methods would still share a footprint.
- Small-N methods (Imaging N=98) have poorly constrained axes; treat their S as noise.
- The dipole is a *directional* first moment; it is insensitive to bi- or quadrupolar
  structure. The C_ℓ spectrum covers those, but only down to the footprint's angular
  resolution (l ≲ 8 is mask-dominated).
- The C_ℓ null is uniform-within-footprint, not a model of within-field detector
  sensitivity; a radial sensitivity gradient inside the Kepler field would survive both
  this null and the permutation null.

## Failed guesses and what they revealed

- **Guess 1: "score vs uniform-sphere null."** Rejected: it measures footprint-ness, not
  world-ness. Revealed the occupancy mask as the true state variable → footprint null.
- **Guess 2: "the preferred axis is the scar."** Rejected after the method split: the
  axis is dominated by Microlensing's bulge crowding. Revealed the per-method audit and
  the Galactic-pole reference as necessary guards.
- **Guess 3: "permute pixel values for the C_ℓ null."** Rejected: permutation preserves
  the exact value multiset, so C_ℓ has near-zero variance and every multipole "saturates"
  against a 100-sample band — a degenerate test. Revealed that the honest null must
  *reassign worlds to random occupied pixels* (destroy structure, keep footprint), which
  gives the meaningful z-scores reported above.

## Generalization

The same pattern — footprint-matched null + per-instrument axis audit + fixed reference
axis — applies to any point distribution on the sphere gathered by surveys: galaxy
catalogs (SDSS footprint), cosmic-ray arrival directions (observatory fields), and
future all-sky exoplanet surveys. The exoplanet machinery in `exoplanets.py` is written
to be reusable for any such catalog.
