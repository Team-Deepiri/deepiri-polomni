#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

commit() {
  local msg="$1"
  shift
  git add "$@"
  git commit -m "$msg"
}

if [ ! -d .git ]; then
  git init
  git checkout -b dev
fi

# ─── Foundation ───────────────────────────────────────────────────────────────
commit "chore: add Apache-2.0 license" LICENSE
commit "docs: add project README" README.md
commit "chore: add Python and research artifact gitignore" .gitignore
commit "chore: add Poetry project configuration" pyproject.toml
commit "chore: add Poetry lockfile for reproducible CI" poetry.lock

# ─── omnifold_core state ──────────────────────────────────────────────────────
commit "feat(core): add omnifold_core package init" \
  src/polomni/core/__init__.py \
  src/polomni/core/state/__init__.py
commit "feat(core): add UnifiedStateVector with Psi stacking" src/polomni/core/state/unified_state.py
commit "feat(core): add StreamPacket pydantic model" src/polomni/core/state/stream_packet.py
commit "feat(core): add ChoiceEvent state transition model" src/polomni/core/state/choice_event.py
commit "feat(core): add conservation closure utilities" src/polomni/core/conservation.py

# ─── omnifold_core conductance ────────────────────────────────────────────────
commit "feat(conductance): add conductance package init" src/polomni/core/conductance/__init__.py
commit "feat(conductance): add bridge tensor coupling" src/polomni/core/conductance/bridge_tensor.py
commit "feat(conductance): add RBLE master equation solver" src/polomni/core/conductance/master_equation.py

# ─── omnifold_core gravity ────────────────────────────────────────────────────
commit "feat(gravity): add gravity package init" src/polomni/core/gravity/__init__.py
commit "feat(gravity): add information tensor field" src/polomni/core/gravity/information_tensor.py
commit "feat(gravity): add modified Einstein field equations" src/polomni/core/gravity/field_equations.py
commit "feat(gravity): add Schwarzschild choice boundary" src/polomni/core/gravity/schwarzschild_choice.py

# ─── omnifold_core inflation ──────────────────────────────────────────────────
commit "feat(inflation): add inflation package init" src/polomni/core/inflation/__init__.py
commit "feat(inflation): add Fokker-Planck evolution operator" src/polomni/core/inflation/fokker_planck.py
commit "feat(inflation): add drift-diffusion inflation model" src/polomni/core/inflation/drift_diffusion.py

# ─── omnifold_core landscape ──────────────────────────────────────────────────
commit "feat(landscape): add landscape package init" src/polomni/core/landscape/__init__.py
commit "feat(landscape): add Kahler metric on moduli space" src/polomni/core/landscape/kahler.py
commit "feat(landscape): add superpotential landscape" src/polomni/core/landscape/superpotential.py
commit "feat(landscape): add vacuum energy calculator" src/polomni/core/landscape/vacuum_energy.py

# ─── omnifold_core radon ──────────────────────────────────────────────────────
commit "feat(radon): add radon package init" src/polomni/core/radon/__init__.py
commit "feat(radon): add S2 Radon transform" src/polomni/core/radon/transform_s2.py
commit "feat(radon): add R3 Radon transform" src/polomni/core/radon/transform_r3.py
commit "feat(radon): add SO(3) rotation utilities" src/polomni/core/radon/so3_rotation.py
commit "feat(radon): add vacuum stream Radon pipeline" src/polomni/core/radon/vacuum_stream.py

# ─── omnifold_core superspace ─────────────────────────────────────────────────
commit "feat(superspace): add superspace package init" src/polomni/core/superspace/__init__.py
commit "feat(superspace): add district graph branching model" src/polomni/core/superspace/district_graph.py
commit "feat(superspace): add branch operator for multiverse splits" src/polomni/core/superspace/branch_operator.py
commit "feat(superspace): add WDW wavefunction generator" src/polomni/core/superspace/wdw_generator.py
commit "feat(superspace): add particle Langevin dynamics" src/polomni/core/superspace/particle_langevin.py

# ─── omnifold_neural ────────────────────────────────────────────────────────────
commit "feat(neural): add omnifold_neural package inits" \
  src/polomni/neural/__init__.py \
  src/polomni/neural/graph_node/__init__.py \
  src/polomni/neural/pinn/__init__.py \
  src/polomni/neural/scar_classifier/__init__.py
commit "feat(neural): add graph node jump engine" src/polomni/neural/graph_node/engine.py
commit "feat(neural): add jump predictor network" src/polomni/neural/graph_node/jump_predictor.py
commit "feat(neural): add PINN metric solver" src/polomni/neural/pinn/metric_solver.py
commit "feat(neural): add RBLE scar classifier scanner" src/polomni/neural/scar_classifier/rble_scanner.py

# ─── omnifold_observatory ─────────────────────────────────────────────────────
commit "feat(observatory): add omnifold_observatory package inits" \
  src/polomni/observatory/__init__.py \
  src/polomni/observatory/ingest/__init__.py \
  src/polomni/observatory/filters/__init__.py \
  src/polomni/observatory/scoring/__init__.py \
  src/polomni/observatory/reports/__init__.py
commit "feat(observatory): add HEALPix map loader" src/polomni/observatory/ingest/healpix_loader.py
commit "feat(observatory): add CMB polarization ingest" src/polomni/observatory/ingest/polarization.py
commit "feat(observatory): add Radon bifurcation filter" src/polomni/observatory/filters/radon_bifurcation.py
commit "feat(observatory): add string landscape filter" src/polomni/observatory/filters/string_filter.py
commit "feat(observatory): add RBLE signature scorer" src/polomni/observatory/scoring/rble_signature.py
commit "feat(observatory): add null ensemble significance test" src/polomni/observatory/scoring/null_ensemble.py
commit "feat(observatory): add detection report generator" src/polomni/observatory/reports/detection_report.py

# ─── omnifold_uqe_bridge ──────────────────────────────────────────────────────
commit "feat(uqe): add UQE bridge package init" src/polomni/bridge/__init__.py
commit "docs(uqe): add UQE bridge integration README" src/polomni/bridge/README.md
commit "feat(uqe): add entanglement entropy bridge" src/polomni/bridge/entanglement.py
commit "feat(uqe): add ER=EPR conductance coupling" src/polomni/bridge/er_epr_coupling.py

# ─── omnifold_cli ─────────────────────────────────────────────────────────────
commit "feat(cli): add omnifold_cli package inits" \
  src/polomni/cli/__init__.py \
  src/polomni/cli/commands/__init__.py
commit "feat(cli): add Typer CLI entrypoint" src/polomni/cli/main.py
commit "feat(cli): add simulate command" src/polomni/cli/commands/simulate.py
commit "feat(cli): add scan command for CMB scars" src/polomni/cli/commands/scan.py
commit "feat(cli): add serve command with FastAPI" src/polomni/cli/commands/serve.py

# ─── visualization ────────────────────────────────────────────────────────────
commit "feat(viz): add visualization package init" src/polomni/viz/__init__.py
commit "feat(viz): add district graph visualization" src/polomni/viz/district_graph_viz.py
commit "feat(viz): add CMB sky map renderer" src/polomni/viz/sky_map.py
commit "feat(viz): add stream pipeline visualization" src/polomni/viz/stream_pipeline_viz.py

# ─── tests package inits ──────────────────────────────────────────────────────
commit "test: add tests package structure" \
  tests/__init__.py \
  tests/unit/__init__.py \
  tests/integration/__init__.py \
  tests/observatory/__init__.py

# ─── unit tests ─────────────────────────────────────────────────────────────────
commit "test(core): add conservation closure unit tests" tests/unit/test_conservation.py
commit "test(core): add unified state vector unit tests" tests/unit/test_unified_state.py
commit "test(conductance): add bridge tensor unit tests" tests/unit/test_conductance_bridge_tensor.py
commit "test(conductance): add master equation unit tests" tests/unit/test_conductance_master_equation.py
commit "test(gravity): add information tensor unit tests" tests/unit/test_gravity_information_tensor.py
commit "test(gravity): add field equations unit tests" tests/unit/test_gravity_field_equations.py
commit "test(gravity): add Schwarzschild choice unit tests" tests/unit/test_gravity_schwarzschild_choice.py
commit "test(inflation): add Fokker-Planck unit tests" tests/unit/test_inflation_fokker_planck.py
commit "test(inflation): add drift-diffusion unit tests" tests/unit/test_inflation_drift_diffusion.py
commit "test(landscape): add Kahler metric unit tests" tests/unit/test_landscape_kahler.py
commit "test(landscape): add superpotential unit tests" tests/unit/test_landscape_superpotential.py
commit "test(landscape): add vacuum energy unit tests" tests/unit/test_landscape_vacuum_energy.py
commit "test(radon): add S2 transform unit tests" tests/unit/test_radon_transform_s2.py
commit "test(radon): add R3 transform unit tests" tests/unit/test_radon_transform_r3.py
commit "test(radon): add SO3 rotation unit tests" tests/unit/test_radon_so3_rotation.py
commit "test(radon): add vacuum stream unit tests" tests/unit/test_radon_vacuum_stream.py
commit "test(superspace): add district graph unit tests" tests/unit/test_district_graph.py
commit "test(superspace): add branch operator unit tests" tests/unit/test_branch_operator.py
commit "test(superspace): add WDW generator unit tests" tests/unit/test_wdw_generator.py
commit "test(superspace): add particle Langevin unit tests" tests/unit/test_particle_langevin.py

# ─── integration & observatory tests ──────────────────────────────────────────
commit "test(integration): add full RBLE loop integration test" tests/integration/test_full_loop.py
commit "test(observatory): add RBLE signature scoring tests" tests/observatory/test_rble_signature.py

# ─── theory docs ──────────────────────────────────────────────────────────────
commit "docs(theory): add notation reference" docs/theory/NOTATION.md
commit "docs(theory): add RBLE master equations" docs/theory/RBLE_MASTER_EQUATIONS.md
commit "docs(theory): add variational principle" docs/theory/VARIATIONAL_PRINCIPLE.md
commit "docs(theory): add falsification criteria" docs/theory/FALSIFICATION_CRITERIA.md
commit "docs(theory): add Radon vacuum pipeline theory" docs/theory/RADON_VACUUM_PIPELINE.md
commit "docs(theory): add superspace branching theory" docs/theory/SUPERSPACE_BRANCHING.md
commit "docs(theory): add string landscape coupling" docs/theory/STRING_LANDSCAPE_COUPLING.md
commit "docs(theory): add CMB observatory mathematics" docs/theory/CMB_OBSERVATORY_MATH.md

# ─── guides & architecture ────────────────────────────────────────────────────
commit "docs(architecture): add system overview" docs/architecture/SYSTEM_OVERVIEW.md
commit "docs(guides): add getting started guide" docs/guides/getting_started.md
commit "docs(guides): add running simulations guide" docs/guides/running_simulations.md
commit "docs(guides): add CMB data pipeline guide" docs/guides/cmb_data_pipeline.md
commit "docs(guides): add UQE bridge integration guide" docs/guides/uqe_bridge.md

# ─── experiments ──────────────────────────────────────────────────────────────
commit "docs(experiments): add district graph branching notebook" experiments/01_district_graph_branching.ipynb
commit "docs(experiments): add Radon vacuum stream notebook" experiments/02_radon_vacuum_stream.ipynb
commit "docs(experiments): add WDW superspace spawn notebook" experiments/03_wdw_superspace_spawn.ipynb
commit "docs(experiments): add Fokker-Planck directed diffusion notebook" experiments/04_fokker_planck_directed_diffusion.ipynb
commit "docs(experiments): add CMB Radon scar scan notebook" experiments/05_cmb_radon_scar_scan.ipynb
commit "docs(experiments): add ER=EPR bridge conductance notebook" experiments/06_er_epr_bridge_conductance.ipynb

# ─── docker ─────────────────────────────────────────────────────────────────────
commit "ci(docker): add Polomni lab Dockerfile" docker/Dockerfile
commit "ci(docker): add docker-compose for local lab" docker/docker-compose.yml

# ─── GitHub CI/CD ───────────────────────────────────────────────────────────────
commit "ci: add pull request template" .github/pull_request_template.md
commit "ci: add poetry-based GitHub Actions workflow" .github/workflows/ci.yml
commit "ci: add CodeQL security scanning workflow" .github/workflows/codeql.yml
commit "ci: add CodeQL paths-ignore configuration" .github/codeql/codeql-config.yml
commit "docs(ci): add CodeQL setup documentation" .github/codeql/README.md

echo "Total commits: $(git rev-list --count HEAD)"
