import sys
import json
import logging
import os
from PyQt5 import uic
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QMainWindow, QMenu, QAction, QFileDialog, QMessageBox, QInputDialog, QTextEdit
from PyQt5.QtCore import Qt, pyqtSignal, QThread
import defs.utils as utils
import defs.saver as saver
import inspect
import argparse

class QTextEditLogger(logging.Handler):
    def __init__(self, widget, log_level):
        super().__init__()
        self.widget = widget
        self.setLevel(log_level)

    def emit(self, record):
        msg = self.format(record)

        # Aplicar color según el nivel del log
        if record.levelno == logging.DEBUG:
            color = 'gray'
        elif record.levelno == logging.INFO:
            color = 'green'
        elif record.levelno == logging.WARNING:
            color = 'orange'
        elif record.levelno == logging.ERROR:
            color = 'red'
        elif record.levelno == logging.CRITICAL:
            color = 'darkred'
        else:
            color = 'black'
        # Añadir el mensaje coloreado y agrupar las líneas del mismo log con un contenedor visible
        self.widget.append(f'''
            <div style="border: 2px solid lightgray; border-radius: 10px; margin: 5px 0; padding: 10px;">
                <p style="color:{color}; margin: 0;">{msg}</p>
            </div>
        ''')
        
class Worker(QThread):
    update = pyqtSignal(int, str, int)
    invoker = pyqtSignal(object, object)

    def __init__(self, parent):
        super(Worker, self).__init__(parent)
        self.parent = parent
        self.model = parent.model
        self._is_running = False

    def run(self):
        invoker = self.invoker.emit
        self._is_running = True
        invoker(self.parent.buttonStartProcess.setEnabled, False)
        # Realizar la consulta en segundo plano
        try:
            self.total_widgets = self.parent.tabInfoToExtract.count()            
            for i in range(self.total_widgets):
                if self._is_running:
                    self.preprompt = self.parent.textPrePrompt.toPlainText()
                    self.json_objetive = self.parent.jsonObjetiveText.toPlainText()
                    try:
                        self.model.load_model(self.preprompt)
                        invoker(self.parent.buttonStartProcess.setText, "Stop Process")
                        invoker(self.parent.buttonStartProcess.setEnabled, True)
                        
                        tab = self.parent.tabInfoToExtract.widget(i)
                        tab_name = self.parent.tabInfoToExtract.tabText(i)
                        invoker(self.parent.statusbar.showMessage,f"Processing tab \'{tab_name}\'. Thile a moment...")
                        #self.parent.logger.info(f"Processing tab \'{tab_name}\'.")
                        text = tab.textInfoToObject.toPlainText()
                        invoker(tab.textResponse.setText, '')
                        invoker(tab.widgetResponse.setVisible, False)
                        invoker(tab.setEnabled, False)
                        
                        images = [tab.image_list.item(i).data(Qt.UserRole) for i in range(tab.image_list.count())]
                        model_response = self.send_query(text, images)
                        response = model_response.text
                        tokens = self.to_int(self.model.model.count_tokens(response))
                        while tokens >=8190:
                            model_response = self.model.query("If you response doesn\'t completed, continue writing the JSON file exactly from where you left off, else only response \"NONE\".")
                            response += model_response.text
                        tokens = self.to_int(self.model.model.count_tokens(response))
                        print(f"Actual Tokens of '{tab_name}': {tokens}")
                        
                        self.update.emit(i, utils.delete_lines(response),0)
                    
                    except Exception as e:
                        if str(e).startswith('403'):
                            print("Error 403: Acceso prohibido en su pais")
                            self.update.emit(i, "Error 403: Access prohibited on your conuntry.", -403)
                            break
                        else:
                            print(f"An error ocurred. {e}")
                            self.update.emit(i, f"An error ocurred. {e}", -404)
                else:
                    invoker(self.parent.buttonStartProcess.setText, "Start Process")
                    invoker(self.parent.buttonStartProcess.setEnabled, False)
                    self.update.emit(i,"Has been stopped by the user.",-1)
            print("All Task Completed.")
            #invoker(self.parent.statusbar.showMessage, "All Task Completed.")
        except Exception as e:
            print(e)
            #invoker(self.parent.statusbar.showMessage, "All Task has fault.")
        self.stop()
        invoker(self.parent.buttonStartProcess.setEnabled, True)
        invoker(self.parent.buttonStartProcess.setText, "Start Process")
        
    
    def stop(self):
        self.invoker.emit(self.parent.buttonStartProcess.setText, "Stopping Process... While a moment...")
        self._is_running = False
        pass
    
    def to_int(self, tokens):
        return int(f"{tokens}".split(": ")[1])
    
    def send_query(self, text, images):
        return self.model.query([f"\'json_objetive\': {self.json_objetive}\n\'text_to_extract\': {text}", *images])
    
class MainW(QMainWindow):
    def __init__(self, ui_log_level):
        super().__init__()
        uic.loadUi('src/ui/main_editor.ui', self)
        self.ui_log_level = ui_log_level
        
        self.load_themes_combobox()  # Cargar los temas en el combobox primero
        self.dataSave = saver.load_config()
        if 'theme' in self.dataSave and self.dataSave['theme']:
            index = self.comboBoxThemes.findText(self.dataSave['theme'])
            if index != -1:
                self.comboBoxThemes.setCurrentIndex(index)
                self.apply_theme(self.dataSave['theme'])
            else:
                # Si el tema guardado no se encuentra, cargar un tema por defecto o no hacer nada
                print(f"Tema guardado '{self.dataSave['theme']}' no encontrado.")
                self.apply_selected_theme()
        else:
            print(f"Error en el tema guardado, cargando uno por defecto...")
            self.apply_selected_theme()
        self.extraUI()
        self.setConectors()

        try:
            self.loadConfig()  # Cargar la configuración, que aplicará el tema guardado
        except Exception as e:
            print(e)
        self.all_ready()
        
    def extraUI(self):
        self.menuAddTabButton = QMenu(self)
        add_tab_with_files_action = QAction("Add Tab with files", self)
        add_new_tab_action = QAction("Add new Tab", self)
        add_tab_with_files_action.triggered.connect(self.add_tab_with_files)
        add_new_tab_action.triggered.connect(self.add_new_tab)
        
        self.menuAddTabButton.addAction(add_tab_with_files_action)
        self.menuAddTabButton.addAction(add_new_tab_action)
        
        self.buttonAddTabInfo.setMenu(self.menuAddTabButton)
        
        self.tabInfoToExtract.tabCloseRequested.connect(self.close_tabInfoToExtract)
        self.json_highlighter_objective = utils.JsonHighlighter(self.jsonObjetiveText.document())
        
        original_text_edit = self.findChild(QTextEdit, 'logTextEdit')
        self.log_text_box = QTextEditLogger(original_text_edit, ui_log_level)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        
        ui_handler = self.log_text_box
        ui_formatter = logging.Formatter('%(levelname)s - %(message)s')
        ui_handler.setFormatter(ui_formatter)
        logger.addHandler(ui_handler)
        
        file_handler = logging.FileHandler('app.log')
        file_formatter = logging.Formatter('%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        self.logger = logger
        self.logger.info("Programa iniciado correctamente...")
        
    def setConectors(self):
        self.leftHideButton.clicked.connect(self.leftHideButtonHandler)
        self.rightHideButton.clicked.connect(self.rightHideButtonHandler)
        self.buttonStartProcess.clicked.connect(self.buttonStartProcessHandler)
        self.buttonReloadModel.clicked.connect(self.buttonReloadModelHandler)
        self.buttonSaveAllTabs.clicked.connect(self.buttonSaveAllTabsHandler)
        
        self.tabInfoToExtract.tabBarDoubleClicked.connect(self.edit_tab_title)
        
        self.lineEditApiKey.editingFinished.connect(self.saveConfig)
        
        self.comboBoxThemes.currentIndexChanged.connect(self.apply_selected_theme)

    def edit_tab_title(self, index):
        if index != -1:
            current_text = self.tabInfoToExtract.tabText(index)
            new_text, ok = QInputDialog.getText(self, "Edit Tab Title", "Enter new title:", text=current_text)
            if ok:
                self.tabInfoToExtract.setTabText(index, new_text)

    def load_themes_combobox(self):
        self.comboBoxThemes.clear()
        themes_dir = "themes"
        print(themes_dir)
        if os.path.exists(themes_dir):
            for filename in os.listdir(themes_dir):
                if filename.endswith(".qss"):
                    theme_name = filename.replace(".qss", "")
                    self.comboBoxThemes.addItem(theme_name)
        else:
            QMessageBox.warning(self, "Warning", f"Theme directory not found: {themes_dir}")

    def apply_theme(self, theme_name):
        if theme_name:
            theme_file = os.path.join("themes", f"{theme_name}.qss")
            try:
                with open(theme_file, "r") as file:
                    self.setStyleSheet(file.read())
            except FileNotFoundError:
                QMessageBox.critical(self, "Error", f"Theme file not found: {theme_file}")

    def apply_selected_theme(self, index=0):
        if index >= 0:
            theme_name = self.comboBoxThemes.currentText()
            self.apply_theme(theme_name)

    def close_tabInfoToExtract(self, index):
        tab = self.tabInfoToExtract.widget(index)
        if tab.isEnabled():
            self.tabInfoToExtract.removeTab(index)
    
    def add_tab_with_files(self):
        """Allows the user to select multiple files or directories and processes them."""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)  # Allows selecting multiple existing files

        # Filters for files and directories
        filters = "Supported Files (*.txt *.json *.xml *.csv);;Text files (*.txt);;JSON files (*.json);;XML files (*.xml);;CSV files (*.csv);;All files (*)"
        file_dialog.setNameFilter(filters)

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        if file_dialog.exec_():
            selected_items = file_dialog.selectedFiles()
            #final_names = [os.path.basename(path) for path in selected_items]
            #formatted_items = "\n<br>".join(f"-- {name}" for name in final_names)
            #self.logger.debug(f"User selected the following items: \n<br>{formatted_items}")
            status_files = {'sucess': [],'error': []}
            for item_path in selected_items:
                if os.path.isfile(item_path):
                    name, status = self.process_file(item_path)
                    status_files[status].append(name)
                elif os.path.isdir(item_path):
                    name, status = self.process_directory(item_path)
                    status_files[status].append(name)
            
            formatted_items_sucess = "\n<br>".join(f"-- {name}" for name in status_files['sucess'])
            formatted_items_errors = "\n<br>".join(f"-- {name}" for name in status_files['error'])
            
            if formatted_items_sucess: self.logger.info(f"Sucess loaded: \n<br>{formatted_items_sucess}")
            if formatted_items_errors: self.logger.info(f"Has errors: \n<br>{formatted_items_errors}")
            
            
    def process_file(self, file_path):
        """Processes an individual file."""
        file_name = os.path.basename(file_path)
        name = os.path.basename(file_path)
        status = 'sucess'
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
            #print(file_content)
            tab = utils.QInfoToExtract(self, file_name, file_content)
            self.tabInfoToExtract.addTab(tab, file_name)
            #self.logger.info(f"Sucess: --{file_path}\n<br>")
            status = 'sucess'
            self.statusbar.showMessage(f"Processed file: {file_name}", 5000)  # Show message for 5 seconds
        except Exception as e:
            error_message = f"Could not read file '{file_name}'. Error: {e}"
            self.logger.error(error_message)
            status = 'error'
            self.statusbar.showMessage(error_message, 10000)  # Show error message for 10 seconds
        return name, status
        
        
    def process_directory(self, dir_path):
        """Processes all valid files within a directory."""
        self.logger.info(f"Processing directory: {dir_path}")
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(('.txt', '.json', '.xml', '.csv')):
                self.process_file(file_path)
        self.logger.info(f"Finished processing directory: {dir_path}")
    
    def add_new_tab(self):
        tab = utils.QInfoToExtract(self)
        self.tabInfoToExtract.addTab(tab, f"Tab #{self.tabInfoToExtract.count()}")
        print("Add new Tab selected")

    def leftHideButtonHandler(self):
        self.hideWidget(self.leftPanel)
        self.leftHideButton.setText("<<<" if self.leftPanel.isVisible() else ">>>")

    def rightHideButtonHandler(self):
        self.hideWidget(self.rightPanel)
        self.rightHideButton.setText(">>>" if self.rightPanel.isVisible() else "<<<")
        
    def buttonStartProcessHandler(self):
        self.progress_bar_no_error()
        widgets_count = self.tabInfoToExtract.count()
        if widgets_count == 0:
            self.statusbar.showMessage("Clear list, impossible to process anything.")
            return
        self.statusbar.showMessage("Checking for internet...")
        self.logger.debug("Checking for internet...")
        if not utils.check_internet():
            self.statusbar.showMessage("You dont have internet access... Enchance your conection and try again...")
            self.logger.warning("No internet access.")
            return
        api_key = self.dataSave['api_key']
        self.statusbar.showMessage("Starting the model... Please Wait...")
        if 'defs.ai' not in sys.modules or not hasattr(sys.modules['defs.ai'], 'geminiClass'):
            print('Importing gemini data model... Wait a few seconds')
            self.logger.debug("Importing geminiClass")
            global geminiClass
            from defs.ai import geminiClass
        else:
            geminiClass = sys.modules['defs.ai'].geminiClass
        
        if api_key and not hasattr(self, 'model'):
            self.model = geminiClass(api_key)
        elif not api_key:
            self.statusbar.showMessage("You may need a valid api key to use the model.")
            return
        
        if not hasattr(self,'worker') or not self.worker._is_running:
            self.buttonStartProcess.setEnabled(False)
            
            self.worker = Worker(self)
            self.progressBarTotal.setValue(0)
            self.progressBarTotal.setMaximum(widgets_count)
            self.worker.update.connect(self.update_task)
            self.worker.invoker.connect(self.method_handler)
            self.worker.start()
        else:
            self.buttonStartProcess.setEnabled(False)
            self.worker.stop()
            self.progress_bar_has_warning()
            #self.worker.wait()  # Esperar a que el subproceso termine completamente
            #self.buttonStartProcess.setEnabled(True)

    
    def buttonReloadModelHandler(self):
        if 'defs.ai' not in sys.modules or not hasattr(sys.modules['defs.ai'], 'geminiClass'):
            print('Importing gemini data model... Wait a few seconds')
            self.logger.debug("Importing geminiClass")
            global geminiClass
            from defs.ai import geminiClass
        else:
            geminiClass = sys.modules['defs.ai'].geminiClass
        self.model = geminiClass(self.dataSave['api_key'])
        self.worker = Worker(self)
        self.all_ready()

    def buttonSaveAllTabsHandler(self):
        tab_count = self.tabInfoToExtract.count()
        if tab_count == 0:
            self.statusbar.showMessage("Nothing to save, you need to create at least one tab.")
            return
        invalid_tabs = []
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly
        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Files", "", options=options)
        if not save_dir:
            return  # User cancelled the directory selection

        for i in range(tab_count):
            tab = self.tabInfoToExtract.widget(i)
            textResponse = tab.textResponse.toPlainText()
            if textResponse:
                tabName = self.tabInfoToExtract.tabText(i)
                # Remove any existing file extension from the tab name
                base_name = os.path.splitext(tabName)[0]
                file_name = f"{base_name}.json"
                file_path = os.path.join(save_dir, file_name)

                try:
                    # Attempt to parse the response as JSON to validate it
                    json.loads(textResponse)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json.loads(textResponse), f, indent=4)  # Save with indentation for readability
                    self.statusbar.showMessage(f"Saved: {file_name}")
                except json.JSONDecodeError:
                    invalid_tabs.append(tabName)
                    self.statusbar.showMessage(f"Error saving: {file_name} - Invalid JSON format")
                except Exception as e:
                    invalid_tabs.append(tabName)
                    self.statusbar.showMessage(f"Error saving: {file_name} - {e}")

        if invalid_tabs:
            invalid_tabs_str = "\n".join(invalid_tabs)
            QMessageBox.warning(self, "Invalid JSON Content",
                                f"The following tabs have invalid JSON content and were not saved:\n{invalid_tabs_str}")
    
    def all_ready(self):
        self.centralTabWidget.setEnabled(True)
        self.buttonStartProcess.setEnabled(True)
    
    def update_task(self, i, response, error_code):
        if i >= 0 and error_code >= 0:
            tab = self.tabInfoToExtract.widget(i)
            tab_name = self.tabInfoToExtract.tabText(i)
            tab.setEnabled(True)
            tab.widgetResponse.setVisible(True)
            tab.textResponse.setText(response)
            self.statusbar.showMessage(f"\'{tab_name}\' has been processed.")
            self.logger.info(f"\'{tab_name}\' has been processed.")
            self.progress_bar_no_error()
        elif error_code == -1:
            print(f"The user has stopped a rest of the process.")
            self.statusbar.showMessage(f"The user has stopped a rest of the process.")
            self.logger.warning(f"The user has stopped a rest of the process.")
            self.progress_bar_has_warning("Stopped...")
        elif error_code == -403:
            self.statusbar.showMessage(response)
            self.logger.error(response)
            self.progress_bar_has_error()
        elif error_code < 0:
            tab_name = self.tabInfoToExtract.tabText(i)
            print(f"an error ocurred on the tab \'{tab_name}\'")
            self.statusbar.showMessage(f"an error ocurred on the tab \'{tab_name}\'")
            self.logger.error(f"an error ocurred on the tab \'{tab_name}: {response}\'")
            self.progress_bar_has_error()
        self.textResponse.setText(response)
        self.progressBarTotal.setValue(self.progressBarTotal.value() + 1)
    
    def progress_bar_no_error(self, msg="%p%"):
        self.progressBarTotal.setFormat(msg)
        self.progressBarTotal.setStyleSheet("")        

    def progress_bar_has_warning(self, msg="%p%"):
        self.progressBarTotal.setFormat(msg)
        self.progressBarTotal.setStyleSheet("""
            QProgressBar::chunk {
                background-color: yellow;
            }
        """)    
    def progress_bar_has_error(self, msg="¡Error! %p%"):
        self.progressBarTotal.setFormat(msg)
        self.progressBarTotal.setStyleSheet("""
            QProgressBar::chunk {
                background-color: red;
            }
        """)

    def hideWidget(self, widget):
        widget.setVisible(not widget.isVisible())
        
    def saveConfig(self):
        self.dataSave['api_key'] = self.lineEditApiKey.text()
        self.dataSave['left_hide_panel'] = self.leftPanel.isVisible()
        self.dataSave['right_hide_panel'] = self.rightPanel.isVisible()
        self.dataSave['theme'] = self.comboBoxThemes.currentText()
        self.dataSave['json_objetive'] = self.jsonObjetiveText.toPlainText()
        saver.save_config(self.dataSave)
        self.logger.debug("Data saved sucessfully.")
    
    def loadConfig(self):
        try:
            self.lineEditApiKey.setText(self.dataSave['api_key'])
            self.leftHideButton.setText("<<<" if self.dataSave['left_hide_panel'] else ">>>")
            self.leftPanel.setVisible(self.dataSave['left_hide_panel'])
            self.rightHideButton.setText(">>>" if self.dataSave['right_hide_panel'] else "<<<")
            self.rightPanel.setVisible(self.dataSave['right_hide_panel'])
            self.jsonObjetiveText.setText(self.dataSave['json_objetive'])
            self.logger.debug("DataLoad loaded sucessfully.")
        except Exception as e:
            self.statusbar.showMessage(str(e))
            self.logger.error(f"DataLoad has a error: {e}")
            print(e)

    def method_handler(self, method, value=None):
        return method(value)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Confirm Exit', "Are you sure you want to exit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.saveConfig()
            self.logger.debug("Closed Sucessfully.")
            event.accept() # Cierra la ventana
        else:
            self.logger.debug("Cancelled.")
            event.ignore() # Ignora el evento de cierre

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    ui_log_level = logging.DEBUG if args.debug else logging.INFO
    
    app = QApplication(sys.argv)
    mainw = MainW(ui_log_level)
    mainw.show()
    print(f"Program id=\'{id(app)}\' launched.")
    
    sys.exit(app.exec_())
    