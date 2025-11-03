import wx
import wx.dataview as dv

from meshsee.fonts import list_system_fonts, split_family_style


class LoadingDialog(wx.Dialog):
    LOADING_DIALOG_DIMS = (400, 100)
    BORDER_SIZE = 12

    def __init__(self, parent: wx.Window | None = None):
        super().__init__(parent, title="Please Wait")
        self.SetSize(wx.Size(*self.LOADING_DIALOG_DIMS))
        self.CentreOnParent()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(self.BORDER_SIZE)
        sizer.Add(
            wx.StaticText(self, label="Loading fonts - this can take some time..."),
            0,
            wx.ALL | wx.ALIGN_CENTER_HORIZONTAL,
            self.BORDER_SIZE,
        )
        sizer.AddSpacer(self.BORDER_SIZE)
        self.SetSizerAndFit(sizer)
        self.Layout()


class FontDialog(wx.Dialog):
    DIALOG_SIZE = (800, 600)
    FONT_NAME_COL_WIDTH = 230
    STYLE_COL_WIDTH = 140
    PATH_COL_WIDTH_MAX = 120
    MARGIN_FOR_BORDERS_SCROLLS = 24
    BUTTON_SPACER_SIZE = 16
    BORDER_SIZE = 8

    def __init__(self, parent: wx.Window | None = None):
        super().__init__(
            parent, title="Meshsee - Fonts", size=wx.Size(*self.DIALOG_SIZE)
        )

        # Widgets
        self.filter_box = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.filter_box.SetHint("Filter by font name...")

        # Single-select DataView; cells are inert (non-editable).
        self.table = dv.DataViewListCtrl(
            self,
            style=wx.BORDER_THEME | dv.DV_SINGLE | dv.DV_ROW_LINES | dv.DV_VERT_RULES,
        )

        # Create columns
        self.col_name = self.table.AppendTextColumn(
            "Font Name", mode=dv.DATAVIEW_CELL_INERT, width=self.FONT_NAME_COL_WIDTH
        )
        self.col_style = self.table.AppendTextColumn(
            "Style", mode=dv.DATAVIEW_CELL_INERT, width=self.STYLE_COL_WIDTH
        )
        self.col_path = self.table.AppendTextColumn(
            "Path",
            mode=dv.DATAVIEW_CELL_INERT,
            width=-1,  # stretch it on resize
        )

        # Enable sorting via the column objects
        self.col_name.SetSortable(True)
        self.col_style.SetSortable(True)
        self.col_path.SetSortable(True)

        self.copy_btn = wx.Button(
            self, label="Copy 'Font Name:style=style' to Clipboard"
        )
        self.ok_btn = wx.Button(self, id=wx.ID_OK, label="OK")
        self.ok_btn.SetDefault()

        # Layout
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(self.copy_btn)
        btn_row.AddSpacer(self.BUTTON_SPACER_SIZE)
        btn_row.Add(self.ok_btn)

        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(self.filter_box, 0, wx.EXPAND | wx.ALL, self.BORDER_SIZE)
        root.Add(self.table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, self.BORDER_SIZE)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, self.BORDER_SIZE)
        self.SetSizer(root)

        # Data store for filtering without re-scanning the system
        self._all_rows: list[tuple[str, str, str]] = []  # (family, style, path)

        # Bindings
        self.filter_box.Bind(wx.EVT_TEXT, self.on_filter_changed)
        self.copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_clicked)
        self.Bind(wx.EVT_SIZE, self.on_resize_stretch_last)

        # Load fonts (with a simple loading dialog)
        self.load_fonts()

        # Make the last column take up remaining space on resize
        self.Layout()
        self.on_resize_stretch_last()

    # ---------- Data loading & filtering ----------

    def load_fonts(self):
        loading = LoadingDialog(self)
        loading.Show()
        wx.Yield()  # let the UI paint the loading dialog

        try:
            fonts = list_system_fonts(duplicate_regular=False)
            # Build and sort once by family (like Qt's initial sort)
            rows: list[tuple[str, str, str]] = []
            for font, path in fonts.items():
                family, style = split_family_style(font)
                rows.append((family, style, path))
            rows.sort(key=lambda r: (r[0].lower(), r[1].lower()))
            self._all_rows = rows
            self._apply_filter()
        finally:
            loading.Destroy()

    def _apply_filter(self):
        """Repopulate the table based on the current filter."""
        needle = self.filter_box.GetValue().strip().lower()
        self.table.DeleteAllItems()
        for family, style, path in self._all_rows:
            if needle in family.lower():
                self.table.AppendItem([family, style, path])

    # ---------- Events ----------

    def on_filter_changed(self, _evt: wx.Event):
        self._apply_filter()

    def on_copy_clicked(self, _evt: wx.Event):
        row = self.table.GetSelectedRow()
        if row == wx.NOT_FOUND:
            wx.MessageBox(
                "Please select a font row.",
                "No Selection",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        name = self.table.GetTextValue(row, 0)
        style = self.table.GetTextValue(row, 1)
        text = f"{name}:style={style}"

        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
        else:
            wx.MessageBox(
                "Could not open the clipboard.",
                "Clipboard Error",
                wx.OK | wx.ICON_ERROR,
                self,
            )

    def on_resize_stretch_last(self, _evt: wx.Event | None = None):
        # Make the last column (Path) stretch to fill remaining width.
        # Compute remaining width after the first two columns and some padding.
        width = self.table.GetClientSize().GetWidth()
        w0 = self.col_name.GetWidth()
        w1 = self.col_style.GetWidth()
        remaining = max(
            self.PATH_COL_WIDTH_MAX, width - (w0 + w1) - self.MARGIN_FOR_BORDERS_SCROLLS
        )
        if remaining != self.col_path.GetWidth():
            self.col_path.SetWidth(remaining)
