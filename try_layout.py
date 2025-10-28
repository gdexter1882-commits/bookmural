def try_layout(wall_w, wall_h, page_w, page_h, pages, margin=0):
    """
    Returns layout metadata if the mural fits within the wall dimensions.
    Enforces:
    - Uniform scaling (aspect ratio preserved)
    - Margins between 5–15 cm
    - Row gap between 1–5 cm
    - Page scaling between 95–105%
    - Centered layout
    """

    for margin_test in range(5, 16):  # test margins from 5 to 15 cm
        usable_w = wall_w - 2 * margin_test
        usable_h = wall_h - 2 * margin_test

        for scale_pct in range(95, 106):  # 95% to 105%
            scaled_pw = page_w * scale_pct / 100
            scaled_ph = page_h * scale_pct / 100

            for row_gap in range(1, 6):  # 1 to 5 cm
                for cols in range(1, pages + 1):
                    rows = (pages + cols - 1) // cols  # ceiling division

                    mural_w = cols * scaled_pw
                    mural_h = rows * scaled_ph + (rows - 1) * row_gap

                    if mural_w <= usable_w and mural_h <= usable_h:
                        margin_x = (wall_w - mural_w) / 2
                        margin_y = (wall_h - mural_h) / 2

                        if not (5 <= margin_x <= 15 and 5 <= margin_y <= 15):
                            continue

                        return {
                            "eligible": True,
                            "grid": f"{rows}x{cols}",
                            "rows": rows,
                            "cols": cols,
                            "scale_pct": scale_pct,
                            "row_gap": row_gap,
                            "margin_x": round(margin_x, 2),
                            "margin_y": round(margin_y, 2),
                            "page_w": round(scaled_pw, 2),
                            "page_h": round(scaled_ph, 2),
                            "text_centered": True
                        }

    return {"eligible": False}