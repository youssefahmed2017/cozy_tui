"""Pure movement/steering math -- no Widget/App involved, so it's unit-
testable in isolation (see tests/test_aquarium.py)."""

import math
import random

from .constants import AVOID_MARGIN, EAT_RADIUS


def random_velocity(speed: float) -> tuple[float, float]:
    angle = random.uniform(0, 2 * math.pi)
    return speed * math.cos(angle), speed * math.sin(angle)


def steer(
    x: float,
    y: float,
    vx: float,
    vy: float,
    bounds: tuple[float, float, float, float],
    dt: float,
) -> tuple[float, float, float, float]:
    """Advance (x, y) by (vx, vy)*dt, bouncing velocity off the `bounds`
    rectangle (x0, y0, x1, y1) -- reflects the position back in rather than
    clamping flat against the wall, so a fast-moving fish doesn't visibly
    stick to the edge for a frame."""
    x0, y0, x1, y1 = bounds
    nx, ny = x + vx * dt, y + vy * dt
    if nx < x0:
        nx = x0 + (x0 - nx)
        vx = -vx
    elif nx > x1:
        nx = x1 - (nx - x1)
        vx = -vx
    if ny < y0:
        ny = y0 + (y0 - ny)
        vy = -vy
    elif ny > y1:
        ny = y1 - (ny - y1)
        vy = -vy
    nx = min(max(nx, x0), x1)
    ny = min(max(ny, y0), y1)
    return nx, ny, vx, vy


def steer_toward_food(vx, vy, fx, fy, food_pos, speed, blend):
    """Blend (vx, vy) toward the direction of ``food_pos`` (an (x, y) tuple,
    or None for "no food exists"), scaled to `speed`. ``blend`` is the
    fraction (0..1) of the way to move this frame -- callers pass something
    like ``min(1.0, RATE * dt)`` so the response is frame-rate independent.
    Returns (vx, vy, ate): ``ate`` is True once within EAT_RADIUS, in which
    case the velocity is left untouched and the caller is responsible for
    removing the food and updating hunger/health."""
    if food_pos is None:
        return vx, vy, False
    tx, ty = food_pos
    dx, dy = tx - fx, ty - fy
    dist = math.hypot(dx, dy)
    if dist <= EAT_RADIUS:
        return vx, vy, True
    tvx, tvy = dx / dist * speed, dy / dist * speed
    return vx + (tvx - vx) * blend, vy + (tvy - vy) * blend, False


def steer_away_from(vx, vy, fx, fy, threat_pos, speed, blend):
    """Blend (vx, vy) directly away from `threat_pos`, unconditionally --
    unlike avoid_decorations(), there's no influence-radius gating (the
    caller decides when it applies). avoid_decorations()'s influence radius
    is sized off AVOID_MARGIN for short-range furniture-bumping, far too
    short for long-range separation like rivals sleeping as far apart as
    the tank allows."""
    dx, dy = fx - threat_pos[0], fy - threat_pos[1]
    dist = math.hypot(dx, dy)
    away_x, away_y = (dx / dist, dy / dist) if dist > 1e-6 else (1.0, 0.0)
    tvx, tvy = away_x * speed, away_y * speed
    return vx + (tvx - vx) * blend, vy + (tvy - vy) * blend


def nearest_index(fx, fy, positions):
    """Index of the closest (x, y) in `positions` to (fx, fy), or None if
    `positions` is empty. Shared by Fish's food-seeking, prey-seeking, and
    (Step 4) decoration-avoidance -- all just "closest point in a list"."""
    if not positions:
        return None
    best_i, best_d2 = 0, None
    for i, (x, y) in enumerate(positions):
        d2 = (x - fx) ** 2 + (y - fy) ** 2
        if best_d2 is None or d2 < best_d2:
            best_i, best_d2 = i, d2
    return best_i


def school_velocity(
    fx,
    fy,
    vx,
    vy,
    neighbors,
    speed,
    blend,
    cohesion_weight,
    alignment_weight,
    separation_weight,
    separation_dist,
):
    """Boids-lite for one frame: `neighbors` is a list of (nx, ny, nvx, nvy)
    for same-species schoolmates already filtered to within schooling range
    by the caller (Fish._schoolmates()). Blends three classic boid rules
    into a single target direction, scaled to `speed`, then blends (vx, vy)
    toward it by `blend` -- the same frame-rate-independent contract every
    other steer_*() here follows:
      - cohesion: steer toward the flock's average position
      - alignment: match the flock's average heading
      - separation: push away from anyone closer than `separation_dist`
    Returns (vx, vy) unchanged if there are no neighbors, or if the three
    rules happen to cancel out exactly (no clear pull either way)."""
    if not neighbors:
        return vx, vy
    n = len(neighbors)
    avg_x = sum(nx for nx, _ny, _nvx, _nvy in neighbors) / n
    avg_y = sum(ny for _nx, ny, _nvx, _nvy in neighbors) / n
    avg_vx = sum(nvx for _nx, _ny, nvx, _nvy in neighbors) / n
    avg_vy = sum(nvy for _nx, _ny, _nvx, nvy in neighbors) / n

    cohesion_x, cohesion_y = avg_x - fx, avg_y - fy
    cohesion_dist = math.hypot(cohesion_x, cohesion_y)
    if cohesion_dist > 1e-6:
        cohesion_x, cohesion_y = cohesion_x / cohesion_dist, cohesion_y / cohesion_dist

    align_dist = math.hypot(avg_vx, avg_vy)
    align_x, align_y = (
        (avg_vx / align_dist, avg_vy / align_dist) if align_dist > 1e-6 else (0.0, 0.0)
    )

    sep_x, sep_y = 0.0, 0.0
    for nx, ny, _nvx, _nvy in neighbors:
        dx, dy = fx - nx, fy - ny
        dist = math.hypot(dx, dy)
        if 0.0 < dist < separation_dist:
            sep_x += dx / dist
            sep_y += dy / dist

    tx = cohesion_x * cohesion_weight + align_x * alignment_weight + sep_x * separation_weight
    ty = cohesion_y * cohesion_weight + align_y * alignment_weight + sep_y * separation_weight
    tdist = math.hypot(tx, ty)
    if tdist < 1e-6:
        return vx, vy  # rules cancel out -- no clear pull, keep the current heading
    tvx, tvy = tx / tdist * speed, ty / tdist * speed
    return vx + (tvx - vx) * blend, vy + (tvy - vy) * blend


def avoid_decorations(vx, vy, fx, fy, decorations, speed, blend):
    """decorations: list of (x, y, radius) tuples -- each's own footprint
    radius, with no margin baked in (AVOID_MARGIN is applied here, the one
    place it's tuned). Finds whichever decoration the fish is nearest to and,
    if within radius + AVOID_MARGIN, blends velocity directly away from it --
    steer_toward_food's blend-toward idea, aimed the other way. Cheap
    repulsion, not real pathfinding (see the Step 4 module-docstring note)."""
    i = nearest_index(fx, fy, [(x, y) for x, y, _r in decorations])
    if i is None:
        return vx, vy
    dx_, dy_, radius = decorations[i]
    ddx, ddy = fx - dx_, fy - dy_
    dist = math.hypot(ddx, ddy)
    influence = radius + AVOID_MARGIN
    if dist >= influence:
        return vx, vy
    away_x, away_y = (ddx / dist, ddy / dist) if dist > 1e-6 else (1.0, 0.0)
    tvx, tvy = away_x * speed, away_y * speed
    return vx + (tvx - vx) * blend, vy + (tvy - vy) * blend
