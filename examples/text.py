from meshsee import text


def create_mesh():
    t = "Abc123"
    font = "Papyrus:style=Condensed"
    return text(
        t, font=font, size=100, valign="bottom", halign="right", direction="rtl"
    ).apply_scale((1.0, 1.0, 10.0))
