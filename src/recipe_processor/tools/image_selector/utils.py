"""Utility-Funktionen spezifisch fuer den Image Selector."""


def transform_coords(coords: tuple, scale_factor: float) -> tuple:
    """Transformiert Display-Koordinaten zurueck auf Original-Koordinaten."""
    x1, y1, x2, y2 = coords
    if scale_factor == 0:
        raise ValueError("scale_factor must be non-zero")
    return (
        int(x1 / scale_factor),
        int(y1 / scale_factor),
        int(x2 / scale_factor),
        int(y2 / scale_factor),
    )
