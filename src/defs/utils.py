import json
import re
import socket
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QTextEdit, QGridLayout,
                            QPushButton, QLabel, QFileDialog, QMenu, QAction, QListWidget,
                            QListWidgetItem
                            )
from PyQt5.QtGui import QPixmap, QContextMenuEvent, QIcon, QDesktopServices, QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import Qt, QUrl, QRegExp

def list_read_beautiful(lst:[]):
    return ', '.join(lst[:-1]) + ' y ' + lst[-1]

def delete_lines(texto):
    lineas = texto.split('\n')
    lineas_filtradas = [linea for linea in lineas if not linea.startswith('```')]
    return '\n'.join(lineas_filtradas)

class ZoomableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super(ZoomableTextEdit, self).__init__(parent)
        self.current_zoom = 1.0  # Factor de zoom acumulativo

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.current_zoom *= 1.1
            else:
                self.current_zoom /= 1.1

            # Limit zoom factor
            self.current_zoom = max(0.5, min(self.current_zoom, 3.0))

            font = self.font()
            font.setPointSizeF(10 * self.current_zoom)  # Ajusta el tamaño de la fuente basado en el factor de zoom
            self.setFont(font)

            # Marca el evento como manejado
            event.accept()
        else:
            super(ZoomableTextEdit, self).wheelEvent(event)


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        # Rules for keywords (true, false, null)
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(Qt.darkBlue))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = ["true", "false", "null"]
        for word in keywords:
            pattern = r'\b%s\b' % word
            self.highlighting_rules.append((pattern, keyword_format))

        # Rules for strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(Qt.darkGreen))
        pattern = r'"[^"]*"'
        self.highlighting_rules.append((pattern, string_format))

        # Rules for numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(Qt.darkRed))
        pattern = r'\b[0-9.-]+\b'
        self.highlighting_rules.append((pattern, number_format))

        # Rules for braces and brackets
        brace_format = QTextCharFormat()
        brace_format.setForeground(QColor(Qt.darkMagenta))
        pattern = r'[{}\[\]]'
        self.highlighting_rules.append((pattern, brace_format))

        # Rules for colons and commas
        punctuation_format = QTextCharFormat()
        punctuation_format.setForeground(QColor(Qt.darkCyan))
        pattern = r'[:,]'
        self.highlighting_rules.append((pattern, punctuation_format))

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

class QInfoToExtract(QWidget):
    def __init__(self, parent=None, file_name="", file_content=""):
        super().__init__(parent)
        self.file_name = file_name
        self.file_content = file_content
        self.zoom_factor = 1.0
        self.initUI()
        self.adjust_list_height()

    def initUI(self):
        # Layouts
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)
        self.text_layout = QHBoxLayout()
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(0)
        self.image_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(2)

        # Widget InfoToObject
        self.widgetInfoToObject = QWidget()
        self.layoutInfoToObject = QVBoxLayout()
        self.layoutInfoToObject.setContentsMargins(0, 0, 0, 0)
        self.layoutInfoToObject.setSpacing(4)
        self.labelInfoToObject = QLabel("Info To Extract:")
        self.textInfoToObject = ZoomableTextEdit()
        self.textInfoToObject.setWordWrapMode(False)
        self.textInfoToObject.setText(self.file_content)
        self.layoutInfoToObject.addWidget(self.labelInfoToObject, alignment=Qt.AlignCenter)
        self.layoutInfoToObject.addWidget(self.textInfoToObject)
        self.widgetInfoToObject.setLayout(self.layoutInfoToObject)
        self.text_layout.addWidget(self.widgetInfoToObject)

        # Widget Response
        self.widgetResponse = QWidget()
        self.layoutResponse = QVBoxLayout()
        self.layoutResponse.setContentsMargins(0, 0, 0, 0)
        self.layoutResponse.setSpacing(4)
        self.labelResponse = QLabel("Response:")
        self.textResponse = ZoomableTextEdit()
        self.textResponse.setWordWrapMode(False)
        self.layoutResponse.addWidget(self.labelResponse, alignment=Qt.AlignCenter)
        self.layoutResponse.addWidget(self.textResponse)
        self.widgetResponse.setLayout(self.layoutResponse)
        self.text_layout.addWidget(self.widgetResponse)
        self.widgetResponse.setVisible(False)

        self.json_highlighter_info = JsonHighlighter(self.textInfoToObject.document())
        self.json_highlighter_response = JsonHighlighter(self.textResponse.document())

        # Área para imágenes
        self.image_list = QListWidget()
        self.image_layout.addWidget(self.image_list)
        self.image_list.itemChanged.connect(self.adjust_list_height)  # Conectar a la señal de cambio de ítem
        self.image_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_list.customContextMenuRequested.connect(self.open_menu)

        # Botones para agregar y quitar imágenes
        self.add_image_button = QPushButton("Agregar Imagen")
        self.clear_image_button = QPushButton("Vaciar Lista")
        self.button_layout.addWidget(self.add_image_button)
        self.button_layout.addWidget(self.clear_image_button)

        # Conectar los botones
        self.add_image_button.clicked.connect(self.add_image)
        self.clear_image_button.clicked.connect(self.clear_images)

        # Añadir layouts al layout principal
        self.main_layout.addLayout(self.text_layout)
        self.main_layout.addLayout(self.image_layout)
        self.main_layout.addLayout(self.button_layout)

    def adjust_list_height(self):
        # Ajustar la altura de la lista basada en el número de ítems, hasta un máximo de 200 píxeles
        max_height = 200
        height = min(self.image_list.sizeHintForRow(0) * self.image_list.count(), max_height)
        self.image_list.setFixedHeight(height)

    def add_image(self):
        # Abrir un cuadro de diálogo para seleccionar imágenes
        options = QFileDialog.Options()
        file_names, _ = QFileDialog.getOpenFileNames(self, "Seleccionar Imagenes", "", "Imagenes (*.png *.jpg *.jpeg *.bmp)", options=options)
        for file_name in file_names:
            if file_name:
                # Añadir la imagen al QListWidget
                item = QListWidgetItem()
                item.setText(file_name)
                item.setData(Qt.UserRole, file_name)
                item.setIcon(QIcon(QPixmap(file_name).scaled(100, 100, Qt.KeepAspectRatio)))
                self.image_list.addItem(item)

        self.adjust_list_height()  # Ajustar la altura después de agregar imágenes

    def clear_images(self):
        self.image_list.clear()
        self.adjust_list_height()  # Ajustar la altura después de vaciar la lista

    def open_menu(self, position):
        context_menu = QMenu(self)
        open_action = QAction("Abrir Imagen", self)
        remove_action = QAction("Quitar Imagen", self)
        context_menu.addAction(open_action)
        context_menu.addAction(remove_action)

        open_action.triggered.connect(self.open_image)
        remove_action.triggered.connect(self.remove_image)

        context_menu.exec_(self.image_list.viewport().mapToGlobal(position))

    def open_image(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            for item in selected_items:
                file_name = item.data(Qt.UserRole)
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_name))

    def remove_image(self):
        selected_items = self.image_list.selectedItems()
        if selected_items:
            for item in selected_items:
                self.image_list.takeItem(self.image_list.row(item))

        self.adjust_list_height()  # Ajustar la altura después de eliminar imágenes

def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Comprueba si hay conexión a Internet intentando conectar a un servidor."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.create_connection((host, port))
        return True
    except OSError:
        return False