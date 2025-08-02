import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTableView,
    QAbstractItemView,
    QMessageBox,
)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QClipboard, QRawFont
from PySide6.QtCore import Qt, QSortFilterProxyModel

from meshsee.fonts import list_system_fonts, split_family_style


class FontFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.filter_string = ""

    def setFilterString(self, text):
        self.filter_string = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(source_row, 0, source_parent)
        font_name = self.sourceModel().data(index)
        return self.filter_string in font_name.lower()


class FontDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Fonts")

        self.model = QStandardItemModel(0, 3)
        self.model.setHorizontalHeaderLabels(["Font Name", "Style", "Path"])

        self.proxy_model = FontFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Filter by font name...")
        self.filter_box.textChanged.connect(self.proxy_model.setFilterString)

        self.copy_button = QPushButton("Copy 'Font Name:style=style' to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        self.load_fonts()

        layout = QVBoxLayout()
        layout.addWidget(self.filter_box)
        layout.addWidget(self.table)
        layout.addWidget(self.copy_button)
        self.setLayout(layout)

    def load_fonts(self):
        for font, path in list_system_fonts(duplicate_regular=False).items():
            family_name, style = split_family_style(font)
            items = [
                QStandardItem(family_name),
                QStandardItem(style),
                QStandardItem(path),
            ]
            # items[0].setFont(QRawFont(path, 10))
            for item in items:
                item.setEditable(False)
            self.model.appendRow(items)
            # try:
            #     font_prop = fm.FontProperties(fname=font)
            #     font_name = font_prop.get_name()
            #     style = font_prop.get_style()
            #     items = [
            #         QStandardItem(font_name),
            #         QStandardItem(style),
            #         QStandardItem(font),
            #     ]
            #     for item in items:
            #         item.setEditable(False)
            #     self.model.appendRow(items)
            # except Exception:
            #     continue  # Some fonts may fail to load

    def copy_to_clipboard(self):
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "No Selection", "Please select a font row.")
            return
        index = indexes[0]
        name = self.proxy_model.data(self.proxy_model.index(index.row(), 0))
        style = self.proxy_model.data(self.proxy_model.index(index.row(), 1))
        text = f"{name}:style={style}"
        QApplication.clipboard().setText(text, QClipboard.Mode.Clipboard)
        # QMessageBox.information(
        #     self,
        #     "Copied",
        #     f"Copied to clipboard:\n{text}",
        #     QMessageBox.StandardButton.Ok,
        # )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = FontDialog()
    dlg.resize(800, 600)
    dlg.exec()
