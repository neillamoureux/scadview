from meshsee import fonts


def test_list_system_fonts_mocks_findSystemFonts(monkeypatch):
    # Mock matplotlib.font_manager.findSystemFonts to return fake font paths
    fake_fonts = [
        "/fake/path/font1.ttf",
        "/fake/path/font2.otf",
        "/fake/path/font3.ttf",
    ]
    monkeypatch.setattr(
        fonts.font_manager, "findSystemFonts", lambda *args, **kwargs: fake_fonts
    )

    # Mock FT2Font to return a fake name
    class FakeFT2Font:
        def __init__(self, font_path):
            self.font_path = font_path

        @property
        def family_name(self):
            if "3" in self.font_path:
                raise ValueError("Corrupted font file")
            if self.font_path == fonts.DEFAULT_FONT_PATH:
                return "Default Font"
            return "FakeFont" + self.font_path[-5]

        @property
        def style_name(self):
            if self.font_path == fonts.DEFAULT_FONT_PATH:
                return "default"
            if "1" in self.font_path:
                return "Regular"
            return "Italic"

    monkeypatch.setattr(fonts.ft2font, "FT2Font", FakeFT2Font)
    fnts = fonts.list_system_fonts()
    assert isinstance(fnts, dict)
    assert "FakeFont1" in fnts.keys()
    assert "FakeFont1:style=Regular" in fnts.keys()
    assert "FakeFont2:style=Italic" in fnts.keys()
    assert "Default Font:style=default" in fnts.keys()
    assert len(fnts) == 4
