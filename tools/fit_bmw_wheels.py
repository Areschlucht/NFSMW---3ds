"""Provisional BMW wheel placement fitted to the original body wheel arches.

This is a BMW-specific geometric estimate, NOT recovered axle metadata.
The original front tire mesh is reused at all four estimated attachments.
"""
import numpy as np


def fit_circle(points, end):
    points = np.asarray(points, dtype=float)
    if len(points) < 12 or not np.isfinite(points).all():
        raise ValueError('Insufficient finite wheel-arch points')
    rng = np.random.default_rng(0)
    best = None
    for _ in range(3000):
        sample = points[rng.choice(len(points), 3, replace=False)]
        try:
            solution = np.linalg.solve(np.column_stack((2 * sample, np.ones(3))), np.sum(sample * sample, axis=1))
        except np.linalg.LinAlgError:
            continue
        center = solution[:2]
        radius2 = solution[2] + sum(center * center)
        if radius2 <= 0:
            continue
        radius = radius2 ** .5
        if not .34 < radius < .5 or not 0 < center[1] < .35 or not .8 < center[0] * end < 1.85:
            continue
        errors = np.abs(np.linalg.norm(points - center, axis=1) - radius)
        selected = errors < .006
        if selected.sum() < 12:
            continue
        score = (int(selected.sum()), -float(np.mean(errors[selected])))
        if best is None or score > best[0]:
            best = score, selected
    if best is None:
        raise ValueError('No supported wheel-arch circle')
    selected = best[1]
    sample = points[selected]
    if np.ptp(sample[:, 0]) < .45 or np.ptp(sample[:, 1]) < .15:
        raise ValueError('Wheel-arch fit lacks geometric coverage')
    solution = np.linalg.lstsq(np.column_stack((2 * sample, np.ones(len(sample)))), np.sum(sample * sample, axis=1), rcond=None)[0]
    center = solution[:2]
    radius = (solution[2] + sum(center * center)) ** .5
    rms = float(np.sqrt(np.mean((np.linalg.norm(sample - center, axis=1) - radius) ** 2)))
    if rms > .006:
        raise ValueError('Wheel-arch fit residual too large')
    return center.tolist(), float(radius), selected, rms


def fit_wheels(body, tire):
    fits = []
    for side in (1, -1):
        for end in (1, -1):
            source = np.unique(np.asarray([p for p in body['positions'] if p[1] * side > .75 and .28 < p[2] < .7 and p[0] * end > .6]), axis=0)
            center, radius, selected, rms = fit_circle(source[:, [0, 2]], end)
            fits.append(dict(side=side, end=end, center_x=center[0], center_z=center[1],
                             arch_radius=radius, outer_y=float(np.max(np.abs(source[selected, 1]))), rms_m=rms))
    # A common axle height keeps four equal recovered tires on one plane.
    height = sum(f['center_z'] for f in fits) / 4
    outer = max(p[1] for p in tire['positions'])
    inner = min(p[1] for p in tire['positions'])
    # Alpha-cut back-face quads have square corners outside the visible disc.
    # Use the axis extent, not their diagonal, for the rolling radius.
    rolling_radius = max(max(abs(p[0]),abs(p[2])) for p in tire['positions'])
    models = []
    for fit in fits:
        side = fit['side']
        offset = fit['outer_y'] - .01 - outer
        name = ('FRONT' if fit['end'] == 1 else 'REAR') + ('_LEFT' if side == 1 else '_RIGHT')
        # The recovered TIRE_BACK surface is at maximum local Y. The rim is
        # toward minimum Y, so increasing local Y must point inward on both
        # sides. Rotate about source Z on the left; preserve orientation right.
        positions = [(fit['center_x'] - side * p[0], side * (fit['outer_y']-.01+inner-p[1]), height + p[2]) for p in tire['positions']]
        bounds = [[min(p[a] for p in positions) for a in range(3)], [max(p[a] for p in positions) for a in range(3)]]
        pivot=(fit['center_x'],height,-side*(offset+(outer+inner)/2))
        models.append(dict(tire, name='PROVISIONAL_TIRE_' + name, positions=positions, stored_bounds=bounds,
                           wheel_pivot=pivot,wheel_radius=rolling_radius,wheel_front=fit['end']==1))
    return models, dict(method='BMW body-arch circle fit, not original axle metadata; front tire mesh reused four times',
                        common_axle_height=height, arch_fits=fits)
