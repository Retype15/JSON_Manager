from PyQt5.QtWidgets import QTabWidget, QTextEdit
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from defs.utils import QInfoToExtract

class DragDropTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            valid_extensions = ['.txt', '.html', '.json', '.py', '.csv', '.xml', '.yaml', '.yml', '.md', '.ini', '.log', '.tsv']
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if not any(file_path.lower().endswith(ext) for ext in valid_extensions):
                    event.ignore()
                    return
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            file_name = 'NaN'
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    file_name = file_path.split('/')[-1]
                    tab = QInfoToExtract(self, file_name, content)
                    self.addTab(tab, file_name)
                    self.parent.statusbar.showMessage(f"Processed file: {file_name}", 5000)
            except Exception as e:
                error_message = f"Could not read file '{file_name}'. Error: {e}"
                self.parent.logger.error(error_message)
                self.parent.statusbar.showMessage(error_message, 10000)
                print(f"Error: {e}")
                file_name = 'NaN'