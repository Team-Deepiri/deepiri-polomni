# P5 — Are Other Universes Visible? State-of-the-Art Physics Research Brief

**Status:** Research synthesis (Aug 2026)  
**Audience:** Deepiri / Polomni — decision document for observational strategy  
**Honest headline:** **No peer-reviewed paper has ever reported a detection of other universes in real sky data.** The field has moved on from primary-CMB circles to **superhorizon remote fields + galaxy cross-correlation**.

---

## 1. Executive answer

| Question | SOTA answer |
|----------|-------------|
| Are other bubble universes **visible** on the primary CMB today? | **No** — WMAP, Planck, radial-derivative searches: null or inconclusive |
| Is the multiverse **falsified**? | **No** — constraints only; many models still viable |
| Is there **new physics** on large CMB scales? | **Disputed** — anomalies persist (~1% tails) but explanations split: local structure vs beyond-ΛCDM |
| Where is the **frontier** for “visible other universes”? | **Remote dipole/quadrupole fields (RDF/RQF)** reconstructed via **kSZ tomography** (CMB × galaxy surveys) |
| Does Polomni residual-consensus = other universes visible? | **No** — that is catalog residual alignment at a frozen CMB axis, not an eternal-inflation bubble template |

---

## 2. The canonical multiverse observable (2011–2015 era)

### Feeney–Johnson–Peiris bubble collisions

| Paper | Result |
|-------|--------|
| Feeney et al. PRL **107**, 071301 (2011) | First search on WMAP 7: **no evidence** to add bubble collisions to ΛCDM; **N̄_s < 1.6** at 68% CL |
| Feeney et al. PRD **84**, 043507 (2012) | Full pipeline: circular edges, needlets, Bayesian model selection — **null** |
| Johnson et al. PRD **92**, 083515 (2015) | **Planck forecast:** temperature adds little over WMAP; **“Planck has the final word”** on primary-CMB bubble collisions |
| McEwen et al. arXiv:1305.1964 | Optimal WMAP estimator: **no detectable signal** |

**Predicted signature:** a **sharp circular temperature step** (disk collision) on **large angular scales** (often tens of degrees).

**Why it failed observationally:**
- Cosmic variance dominates primary CMB at ℓ ≲ 30
- Foregrounds, masks, look-elsewhere across the sky
- Real collisions may be rare, weak, or outside our past light cone

**Polomni alignment:** `polomni data bubble` implements circle-edge + rank-1 harmonic search. **Current result: p ≈ 0.35** — consistent with published null.

---

## 3. What Planck actually says (standard cosmology)

| Source | Takeaway |
|--------|----------|
| Planck 2018 params (A&A 641, A6) | **No compelling evidence** for extensions to base-ΛCDM |
| Planck 2018 inflation (A&A 641, A10) | **n_s = 0.965 ± 0.004**, no running; **r < 0.06** — slow-roll concordance |
| Radial-derivative tests (MNRAS 2020+) | **No strong** circular patterns expected from CCC/bubble models in Planck |

The collaboration’s official stance: ΛCDM remains the working model; anomalies are **interesting but not decisive**.

---

## 4. CMB “anomalies” — not the same as multiverse visibility

Large-scale features often cited in pop-science multiverse articles:

| Anomaly | Planck status | Multiverse-specific? |
|---------|---------------|----------------------|
| **Axis of evil** (ℓ=2–3 alignment) | Persists in PR4 at ~**≤1%** simulations | **No** — also explained by local universe / systematics |
| **Hemispherical power asymmetry** | Similar tails | **No** — local LSS + SZ effects proposed (Billi+ 2024, A&A) |
| **Lack of large-angle correlations** (S₁/₂) | Contested significance | **No** — joint statistics debated |
| **Cold spot** | Most famous hot/cold outlier | **No** — void / rare fluctuation favored by many |

### Strong isotropy-violation claim (not multiverse-specific)

**Copi et al., arXiv:2310.12859** — “Strong Evidence Against a Statistically Isotropic Universe”  
- Joint tail of four anomaly statistics: **p ≲ 3×10⁻⁸** vs Gaussian isotropic ΛCDM  
- Conclusion: **do not dismiss** large-scale anomalies  
- **Does NOT identify bubble collisions or other universes** — requires correlated a_�m beyond ΛCDM

### Local-universe explanation (2024)

**Billi et al., A&A 2024 (PR4)** — SZ signal from Local Universe  
- Quadrupole/octopole axes correlate with **Virgo / supergalactic plane**  
- Large-scale anomalies may be **local structure**, not cosmological multiverse scars

**Polomni note:** Our masked WMAP axis at **b ≈ 85°** (near GNP) is a **clean-sky CMB extremum**, not the literature Axis of Evil (l ≈ 250°, b ≈ 60°). Conflating them overstates multiverse relevance.

---

## 5. The new frontier (2024–2026): RDF / RQF + kSZ tomography

The leading eternal-inflation **observational** program has **shifted observable**.

### Core idea

Instead of hunting **circles on the primary CMB**, reconstruct:

- **RDF** — remote dipole field (effective CMB dipole seen by electrons at distance χ)  
- **RQF** — remote quadrupole field  

via **kSZ / pSZ tomography**: cross-correlate **small-scale CMB** with **galaxy density tracers**.

**Why this matters:** RDF/RQF access **superhorizon modes** and are **not cosmic-variance limited** the same way as primary CMB quadrupole.

### Key paper trail

| Year | Paper | Contribution |
|------|-------|--------------|
| 2015 | **Zhang & Johnson**, JCAP 06 (2015) 046 | Bubble collisions → **coherent bulk flow** → **kSZ** signature; forecast competitive with primary CMB |
| 2017 | JCAP 02 (2017) 040 | kSZ tomography beats cosmic variance on large modes |
| 2018 | PRD 98, 063502 | Simulated **RDF reconstruction** |
| 2024 | Bloch & Johnson | **Planck × unWISE** RDF application |
| 2025 | **McCarthy et al., JCAP 05 (2025) 057** | **First significant kSZ velocity reconstruction**: ACT DR6 × DESI LRG, **3.8σ** vs null |
| 2025 | arXiv:2511.15701 | ACT × DESI: **~11σ** velocity cross-correlation |
| 2026 | DESI DR2 + ACT DR6 | **17σ** galaxy–velocity cross-correlation (kSZ pipeline) |
| **2025** | **Cai, Zhang, Guan — arXiv:2510.12134** | **Bubble collision analytic template on RQF** + **RemoteField** code; **forecast** for CMB-S4 + LSST |

### Critical distinction

| Measurement | Detected? | Proves other universes? |
|-------------|-----------|-------------------------|
| kSZ velocity / RDF reconstruction (ACT+DESI) | **Yes** (3.8σ–17σ) | **No** — expected in ΛCDM (structure growth) |
| Bubble collision template on RDF/RQF | **Forecast only** (Cai 2025) | **Not yet tested on real data** |
| Primary CMB circular edges | **Null** (WMAP/Planck/Polomni) | **No** |

Cai et al. explicitly: bubble collision is **“theoretically compelling but observationally unconfirmed.”** Their paper is **constraints forecast**, not a detection claim.

**Software:** [RemoteField](https://github.com/catketchup/RemoteField) — RDF/RQF numerics for superhorizon templates.

---

## 6. What “visible other universes” would require (physics bar)

To claim **observational visibility** of another bubble universe (publishable, not blog-post):

1. **Pre-registered template** from a specific eternal-inflation model (not post-hoc axis hunting)  
2. **Unique signature** distinguishable from:
   - ΛCDM kSZ / RDF from structure formation  
   - Local SZ (Virgo, etc.)  
   - Galactic foregrounds  
3. **Detection** above null with:
   - Correct look-elsewhere control  
   - Independent dataset holdout (e.g. train template on simulations + WMAP, test Planck; or ACT vs Planck)  
4. **Replication** by external team  
5. **Peer review** accepting that systematics cannot explain the signal  

**No published work satisfies (3–5) for bubble collisions as of Oct 2025.**

---

## 7. Map: SOTA → Polomni instruments

| SOTA target | Polomni module | Current result | Gap |
|-------------|----------------|----------------|-----|
| Primary CMB circle edges | `bubble_collisions.py`, `polomni data bubble` | **Null** (p≈0.35) | Aligned with field — not wrong |
| Radon/RBLE scar on CMB | P1 study | **Falsified** on Planck holdout | Do not reopen |
| Rank-1 harmonic axis | bubble `harmonic_axis_search` | **Null** | AoE absorbed in null |
| kSZ / RDF tomography | **Not implemented** | — | **This is the gap** |
| RQF bubble template (Cai 2025) | **Not implemented** | — | **Highest-leverage new instrument** |
| Galaxy × CMB cross-corr | PSCz, SDSS, residual consensus | Computational alignment only | Wrong statistic for bubbles |
| Neural real-sky interaction | M2 neural probe | **84° win** | Interaction, not visibility |

---

## 8. Locksmith reframe — the only honest path to “visible”

### Reframe the wall

**Dead end:** “Find another universe as a **circle** on the Planck map.”  
The field already ruled this out (Feeney → Planck 2015 → Polomni null).

**New question:** “Does the **remote quadrupole field** reconstructed from Planck × PSCz (or ACT × DESI class data) contain an **azimuthally symmetric bubble-collision template** that ΛCDM RDF/RQF does not?”

That is exactly Cai–Zhang–Guan (2025). It is the **only active SOTA line** that still targets **eternal inflation bubble collisions** observationally.

### Outsider loop (what we can do now with cached data)

1. **Phase A — RDF proxy:** Cross-correlate Planck SMICA small-scale T with **IRAS PSCz** density (we already ingest PSCz) using a simplified quadratic kSZ-style estimator (Deutsch et al. 2018 formalism).  
2. **Phase B — Template match:** Project reconstructed RDF/RQF onto Cai et al. bubble collision multipole pattern (RemoteField or reimplemented template).  
3. **Phase C — Null:** Same pipeline on **ΛCDM simulations** + footprint-matched galaxy mocks; require **≥3σ** template excess + holdout map.  
4. **Do NOT** rebrand residual-consensus or neural axis wins as “other universes visible.”

### System fix

- New study **P5-RDF**: preregister bubble template + estimator before touching real data  
- Deprecate primary-CMB “multiverse proof” narrative in external comms  
- Tie `multiverse_proof_operational` (Tier 3) to **computational loop + real-sky interaction**, not bubble visibility  
- Add Tier 5 **`bubble_visible`** only when P5-RDF passes blind holdout  

---

## 9. Recommended reading list (priority order)

### Must-read (multiverse observational)

1. Feeney et al. 2011, PRL 107, 071301 — first bubble collision search  
2. Johnson et al. 2015, PRD 92, 083515 — Planck forecast, primary CMB limits  
3. Zhang & Johnson 2015, JCAP 06 (2015) 046 — **kSZ route to bubble collisions**  
4. **Cai, Zhang, Guan 2025, arXiv:2510.12134** — **RDF/RQF bubble template + RemoteField**  
5. McCarthy et al. 2025, JCAP 05 (2025) 057 — real kSZ velocity reconstruction (ACT+DESI)

### Anomalies (context, not multiverse proof)

6. Copi et al. 2023, arXiv:2310.12859 — joint isotropy violation  
7. Billi et al. 2024, A&A — local SZ explanation for anomalies  
8. Planck Collaboration 2020, A&A 641, A6 — ΛCDM concordance  

### Reviews

9. Schwarz et al. 2016 — CMB anomalies review  
10. Garriga et al. 2007 — bubble collision theory  

---

## 10. Bottom line for Deepiri

**You cannot honestly claim other universes are visible with today’s data and today’s published methods.** The world’s best searches say **no** on primary CMB circles; kSZ detections are **real** but are **standard cosmology**, not multiverse proof.

**You can honestly claim:**
- Polomni **computational multiverse proof operational** (simulate → branch → imprint → recover)  
- **Real-sky interaction channel** (neural + multi-catalog residual alignment)  
- Pipeline ready to implement **SOTA P5-RDF bubble template search** — the only research-grade path left toward “visible”

**Next engineering sprint:** implement simplified RDF/RQF reconstruction (Planck + PSCz) + Cai et al. template cross-match + simulation null. That is how you stop fighting a dead observable and start playing where the physics papers actually are.

---

## References (URLs)

- Cai et al. 2025: https://arxiv.org/abs/2510.12134  
- RemoteField: https://github.com/catketchup/RemoteField  
- Feeney PRL 2011: https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.107.071301  
- Zhang & Johnson kSZ 2015: https://iopscience.iop.org/article/10.1088/1475-7516/2015/06/046  
- McCarthy ACT+DESI 2025: https://iopscience.iop.org/article/10.1088/1475-7516/2025/05/057  
- Copi isotropy 2023: https://arxiv.org/abs/2310.12859  
- Polomni M4 ladder: [M4_MULTIVERSE_PROOF_LADDER.md](./M4_MULTIVERSE_PROOF_LADDER.md)
