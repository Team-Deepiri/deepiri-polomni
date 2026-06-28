"""Branching Langevin evolution with delta kicks at choice times (RBLE Eq. 9)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class LangevinTrajectory:
    """Recorded branching Langevin trajectory."""

    t: NDArray[np.floating]
    x: NDArray[np.floating]
    p: NDArray[np.floating]


class BranchingLangevinEvolver:
    r"""Overdamped-branching Langevin evolver for district momentum dynamics.

    Evolves conjugate momentum ``p`` and configuration ``x`` with

        \dot{x} = p/m,   \dot{p} = -\nabla V(x) + \sqrt{2D}\,\eta(t),

    and applies a choice delta-kick at each bifurcation time ``t_{\mathrm{choice}}``:

        p \to p + \Delta_k,   \Delta_k = \frac{\Phi_{\mathrm{stream}}}{N}\,(k+1).

    The kick models instantaneous Wheeler-DeWitt momentum injection when the
    district graph branches.
    """

    def __init__(self, mass: float = 1.0, diffusion: float = 0.0, seed: int | None = None) -> None:
        self.mass = float(mass)
        self.diffusion = float(diffusion)
        self._rng = np.random.default_rng(seed)

    def step(
        self,
        p: NDArray[np.floating],
        x: NDArray[np.floating],
        dt: float,
        grad_V: NDArray[np.floating],
        num_choices: int,
        t_choice: float | None = None,
        t_current: float = 0.0,
        t_next: float | None = None,
        kick_scale: float = 1.0,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
        """Advance one Langevin step, optionally applying a delta kick.

        Parameters
        ----------
        p, x:
            Momentum and position vectors.
        dt:
            Time step ``Δt``.
        grad_V:
            Gradient of the landscape potential at ``x``.
        num_choices:
            Branch count ``N`` for scaling the delta kick.
        t_choice:
            Choice event time; kick fires when ``t_current < t_choice <= t_next``.
        t_current:
            Time at the start of the step.
        t_next:
            Time at the end of the step (defaults to ``t_current + dt``).
        kick_scale:
            Overall amplitude of the momentum delta kick.

        Returns
        -------
        tuple[NDArray, NDArray]
            Updated ``(p, x)`` after the step.
        """
        if dt <= 0.0:
            raise ValueError("dt must be positive")
        if num_choices < 1:
            raise ValueError("num_choices must be >= 1")

        t_end = t_current + dt if t_next is None else t_next
        p_out = np.asarray(p, dtype=float).copy()
        x_out = np.asarray(x, dtype=float).copy()
        grad = np.asarray(grad_V, dtype=float)

        noise = self._rng.normal(size=p_out.shape) if self.diffusion > 0.0 else 0.0
        p_out = p_out + dt * (-grad + np.sqrt(2.0 * self.diffusion) * noise)
        x_out = x_out + dt * p_out / self.mass

        if t_choice is not None and t_current < t_choice <= t_end:
            kick = kick_scale * np.arange(1, num_choices + 1, dtype=float) / num_choices
            if kick.size != p_out.size:
                kick = np.resize(kick, p_out.shape)
            p_out = p_out + kick

        return p_out, x_out

    def evolve_trajectory(
        self,
        initial_p: NDArray[np.floating],
        initial_x: NDArray[np.floating],
        t_span: tuple[float, float],
        choice_times: list[float],
        num_choices_each: list[int],
        n_steps: int = 100,
        grad_V_fn: callable | None = None,
        kick_scale: float = 1.0,
    ) -> LangevinTrajectory:
        """Integrate a full trajectory with delta kicks at specified choice times.

        Parameters
        ----------
        initial_p, initial_x:
            Initial momentum and position.
        t_span:
            ``(t_start, t_end)`` integration interval.
        choice_times:
            Sorted list of choice event times.
        num_choices_each:
            Branch count at each choice event (same length as ``choice_times``).
        n_steps:
            Number of uniform time steps.
        grad_V_fn:
            Callable ``x ↦ ∇V(x)``; defaults to harmonic ``∇V = x``.
        kick_scale:
            Delta-kick amplitude scaling.

        Returns
        -------
        LangevinTrajectory
            Recorded times, positions, and momenta.
        """
        if len(choice_times) != len(num_choices_each):
            raise ValueError("choice_times and num_choices_each must have the same length")

        t_start, t_end = t_span
        if t_end <= t_start:
            raise ValueError("t_span end must exceed start")

        times = np.linspace(t_start, t_end, n_steps + 1)
        dt = times[1] - times[0]

        p = np.asarray(initial_p, dtype=float).copy()
        x = np.asarray(initial_x, dtype=float).copy()

        p_hist = np.zeros((n_steps + 1, p.size), dtype=float)
        x_hist = np.zeros((n_steps + 1, x.size), dtype=float)
        p_hist[0] = p
        x_hist[0] = x

        choice_map = dict(zip(choice_times, num_choices_each))

        def default_grad(pos: NDArray[np.floating]) -> NDArray[np.floating]:
            return np.asarray(pos, dtype=float)

        grad_fn = grad_V_fn or default_grad

        for i in range(n_steps):
            t_cur = float(times[i])
            t_nxt = float(times[i + 1])
            t_choice = None
            n_choices = 1

            for tc, nc in choice_map.items():
                if t_cur < tc <= t_nxt:
                    t_choice = tc
                    n_choices = nc
                    break

            p, x = self.step(
                p,
                x,
                dt,
                grad_fn(x),
                num_choices=n_choices,
                t_choice=t_choice,
                t_current=t_cur,
                t_next=t_nxt,
                kick_scale=kick_scale,
            )
            p_hist[i + 1] = p
            x_hist[i + 1] = x

        return LangevinTrajectory(t=times, x=x_hist, p=p_hist)
