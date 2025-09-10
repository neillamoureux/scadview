from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QClipboard, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from meshsee.fonts import list_system_fonts, split_family_style


class FontFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self._filter_string = ""

    def setFilterString(self, text: str):
        self._filter_string = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(
        self, source_row: int, source_parent: QModelIndex | QPersistentModelIndex
    ) -> bool:
        index = self.sourceModel().index(source_row, 0, source_parent)
        font_name = self.sourceModel().data(index)
        return self._filter_string in font_name.lower()


class FontDialog(QDialog):
    DIALOG_SIZE = (800, 600)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meshsee - Fonts")
        self.resize(*self.DIALOG_SIZE)
        self._set_up_font_table()
        self._set_up_filter()
        self._set_up_copy_button()
        self._load_fonts()
        self._set_up_layout()

    def _set_up_font_table(self):
        self._model = QStandardItemModel(0, 3)
        self._model.setHorizontalHeaderLabels(["Font Name", "Style", "Path"])

        self._proxy_model = FontFilterProxyModel()
        self._proxy_model.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy_model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._table.verticalHeader().setVisible(False)

    def _set_up_filter(self):
        self._filter_box = QLineEdit()
        self._filter_box.setPlaceholderText("Filter by font name...")
        self._filter_box.textChanged.connect(self._proxy_model.setFilterString)

    def _set_up_copy_button(self):
        self._copy_button = QPushButton("Copy 'Font Name:style=style' to Clipboard")
        self._copy_button.clicked.connect(self._copy_to_clipboard)

    def _load_fonts(self):
        loading = LoadingDialog(self)
        loading.show()
        QApplication.processEvents()  # Force UI to update before loading starts

        for font, path in list_system_fonts(duplicate_regular=False).items():
            family_name, style = split_family_style(font)
            items = [
                QStandardItem(family_name),
                QStandardItem(style),
                QStandardItem(path),
            ]
            for item in items:
                item.setEditable(False)
            self._model.appendRow(items)
        loading.accept()  # Close the dialog after loading

    def _set_up_layout(self):
        layout = QVBoxLayout()
        layout.addWidget(self._filter_box)
        layout.addWidget(self._table)
        layout.addWidget(self._copy_button)
        self.setLayout(layout)

    def _copy_to_clipboard(self):
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "No Selection", "Please select a font row.")
            return
        index = indexes[0]
        name = self._proxy_model.data(self._proxy_model.index(index.row(), 0))
        style = self._proxy_model.data(self._proxy_model.index(index.row(), 1))
        text = f"{name}:style={style}"
        QApplication.clipboard().setText(text, QClipboard.Mode.Clipboard)


class LoadingDialog(QDialog):
    LOADING_DIALOG_DIMS = (400, 100)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Please Wait")
        self.setModal(True)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Loading fonts - this can take some time..."))
        self.setLayout(layout)
        self.setFixedSize(*self.LOADING_DIALOG_DIMS)
