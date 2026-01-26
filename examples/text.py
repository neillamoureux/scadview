from scadview import text


def create_mesh():
    t = "SCADview"
    font = "Papyrus:style=Condensed"
    return text(
        t,
        font=font,
        size=100,
        valign="bottom",
        halign="right",
        direction="ltr",
    ).apply_scale((1.0, 1.0, 10.0))
