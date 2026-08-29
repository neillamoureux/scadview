"""Feature controls and Debug features example.

Load this script, then select Debug features in the Features section to inspect
enabled feature source geometry. The toggle is separate from each feature's
enabled state.
"""

from trimesh.creation import box, cylinder

from scadview import feature, feature_default

feature_default("handle", enabled=False)


@feature("cutout")
def cable_cutout():
    """Create the subtractive cable-routing tool volume."""
    return cylinder(radius=4.0, height=24.0).apply_translation([0.0, 0.0, 6.0])


def create_mesh():
    base = box([48.0, 24.0, 8.0])
    handle = feature(
        "handle", box([18.0, 8.0, 18.0]).apply_translation([0.0, 0.0, 13.0])
    )

    support_a = feature(
        "supports",
        box([4.0, 4.0, 20.0]).apply_translation([-18.0, -8.0, 14.0]),
    )
    support_b = feature(
        "supports",
        box([4.0, 4.0, 20.0]).apply_translation([18.0, -8.0, 14.0]),
    )

    return (
        base.union(handle).union(support_a).union(support_b).difference(cable_cutout())
    )
