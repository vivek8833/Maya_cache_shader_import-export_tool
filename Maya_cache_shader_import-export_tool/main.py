import sys
import os
import subprocess
import threading
import json
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLineEdit,
    QListView,
    QMessageBox,
    QAbstractItemView
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QStringListModel


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.ui_path = os.path.join(self.BASE_DIR, "ui_form", "my_ui.ui")
        self.sharder_script = os.path.join(self.BASE_DIR, "script", "sharder_export.py")
        self.cache_script = os.path.join(self.BASE_DIR, "script", "cache_script.py")
        self.cache_sharder_script = os.path.join(self.BASE_DIR, "script", "cache_sharder_script.py")
        self.load_ui()
        self.setup_widgets()
        self.setup_styles()
        self.setup_connections()

    def load_ui(self):
        loader = QUiLoader()
        ui_file = QFile(self.ui_path)

        if not ui_file.exists():
            raise FileNotFoundError(f"UI file not found: {self.ui_path}")

        ui_file.open(QFile.ReadOnly)
        self.window = loader.load(ui_file, self)
        ui_file.close()

        self.window.show()

    def setup_widgets(self):
        self.listView_Sharder = self.window.findChild(QListView, "listView_Sharder")
        self.listView_Cache = self.window.findChild(QListView, "listView_Cache")
        self.Sharder_line = self.window.findChild(QLineEdit, "Sharder_line")
        self.Cache_line = self.window.findChild(QLineEdit, "Cache_line")
        self.Import_view = self.window.findChild(QLineEdit, "Import_view")
        self.Check_one = self.window.findChild(QPushButton, "Check_one")
        self.Check_two = self.window.findChild(QPushButton, "Check_two")
        self.button_Sharder = self.window.findChild(QPushButton, "Sharder_Button")
        self.button_Cache = self.window.findChild(QPushButton, "Cache_Button")
        self.button_Cac_shd = self.window.findChild(QPushButton, "Cache_Sharder_Button")
        self.listView_Sharder.model = QStringListModel()
        self.listView_Sharder.setModel(self.listView_Sharder.model)
        self.listView_Sharder.files = []
        self.listView_Cache.model = QStringListModel()
        self.listView_Cache.setModel(self.listView_Cache.model)
        self.listView_Cache.files = []
        self.listView_Sharder.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listView_Cache.setSelectionMode(QAbstractItemView.ExtendedSelection)
    def setup_styles(self):
        self.window.setStyleSheet("background-color: lightblue;")

        button_style = (
            "background-color: gray;"
            "color: white;"
            "font-weight: semi-bold;"
            "border-style: outset;"
            "border-width: 2px;"
            "border-color: black;"
        )

        self.button_Sharder.setStyleSheet(button_style)
        self.button_Cache.setStyleSheet(button_style)
        self.button_Cac_shd.setStyleSheet(button_style)
        self.Check_one.setStyleSheet(button_style)
        self.Check_two.setStyleSheet(button_style)

        self.Sharder_line.setStyleSheet("border: 1.4px solid #36454F;")
        self.Cache_line.setStyleSheet("border: 1.4px solid #36454F;")
        self.listView_Sharder.setStyleSheet("border: 1.4px solid #6a7ea9;")
        self.listView_Cache.setStyleSheet("border: 1.4px solid #6a7ea9;")
        self.Import_view.setStyleSheet("border: 1.5px solid #5a5ea1;")

    def setup_connections(self):
        self.Check_one.clicked.connect(
            lambda: self.load_ma_files(self.Sharder_line, self.listView_Sharder)
        )
        self.Check_two.clicked.connect(
            lambda: self.load_ma_files(self.Cache_line, self.listView_Cache)
        )

        self.button_Sharder.clicked.connect(self.open_selected_maya_with_sharder)
        self.button_Cache.clicked.connect(self.open_selected_maya_with_cache)
        self.button_Cac_shd.clicked.connect(self.run_cache_sharder_script)

    def load_ma_files(self, line_edit, list_view):
        folder = line_edit.text().strip()

        if not os.path.isdir(folder):
            print("Invalid folder:", folder)
            return

        names, paths = [], []

        for file in os.listdir(folder):
            if file.lower().endswith(".ma"):
                names.append(file)
                paths.append(os.path.join(folder, file))

        list_view.model.setStringList(names)
        list_view.files = paths

    def get_maya_version(self, maya_scene_file):
        try:
            with open(maya_scene_file, "r") as f:
                first_line = f.readline().strip()
        except Exception as e:
            print("Failed to read file:", e)
            return None

        for year in range(2022, 2027):
            if first_line.startswith(f"//Maya ASCII {year}"):
                return year
        return None

    def open_maya_sequentially(self, files, script_path):
        total_files = len(files)
        print(f"Starting batch process for {total_files} file(s)...\n")

        for idx, file_path in enumerate(files, start=1):
            print(f"[{idx}/{total_files}] Processing: {file_path}")

            # Determine Maya version
            year = self.get_maya_version(file_path)
            if not year:
                print(f"   Skipping (version not found): {file_path}\n")
                continue

            maya_exe = rf"C:\Program Files\Autodesk\Maya{year}\bin\maya.exe"
            if not os.path.exists(maya_exe):
                print(f"   Skipping (Maya not found): {maya_exe}\n")
                continue

            script_path_maya = script_path.replace("\\", "/")
            file_path_maya = file_path.replace("\\", "/")

            # Maya command: inject scene_path
            maya_command = (
                f'python("scene_path = r\'{file_path_maya}\'; '
                f'exec(open(r\'{script_path_maya}\').read())")'
            )

            print(f"  Launching Maya {year}...\n")
            process = subprocess.Popen([maya_exe, "-command", maya_command])
            process.wait()  # Wait for this Maya instance to finish

            print(f"  Finished: {file_path}\n")

        print("Batch process completed for all files.")


    def open_selected_maya_with_sharder(self):
        indexes = self.listView_Sharder.selectedIndexes()
        if not indexes:
            print("No files selected")
            return

        rows = sorted(index.row() for index in indexes)
        files = [self.listView_Sharder.files[row] for row in rows]

        threading.Thread(
            target=self.open_maya_sequentially,
            args=(files, self.sharder_script),
            daemon=True
        ).start()

    def open_selected_maya_with_cache(self):
        indexes = self.listView_Cache.selectedIndexes()
        if not indexes:
            print("No files selected")
            return

        rows = sorted(index.row() for index in indexes)
        files = [self.listView_Cache.files[row] for row in rows]

        threading.Thread(
            target=self.open_maya_sequentially,
            args=(files, self.cache_script),
            daemon=True
        ).start()

    def run_cache_sharder_script(self):
        folder = self.Import_view.text().strip()
        print("Folder entered:", folder)

        folder = folder.strip('"').strip("'")
        folder = os.path.abspath(os.path.normpath(folder))
        print("Normalized folder path:", folder)
        if not os.path.isdir(folder):
            QMessageBox.warning(
                self.window,
                "Invalid Directory",
                f"The directory path is invalid:\n{folder}"
            )
            return
        json_file = None
        for file in os.listdir(folder):
            if file.lower().endswith("scene_lit.json"):
                json_file = os.path.join(folder, file)
                break

        if not json_file:
            QMessageBox.warning(
                self.window,
                "JSON Not Found",
                "No 'scene_lit.json' found in the selected directory."
            )
            return

        print("JSON Found:", json_file)
        try:
            with open(json_file, "r") as f:
                json_data = json.load(f)
            maya_version = json_data.get("File_info", {}).get("maya_version")
            if not maya_version:
                QMessageBox.critical(
                    self.window,
                    "Maya Version Missing",
                    f"'maya_version' key not found in JSON:\n{json_file}"
                )
                return

        except Exception as e:
            QMessageBox.critical(
                self.window,
                "JSON Read Error",
                f"Failed to read JSON file:\n{json_file}\n\nError: {e}"
            )
            return

        maya_exe = rf"C:\Program Files\Autodesk\Maya{maya_version}\bin\maya.exe"
        print("Maya Executable:", maya_exe)
        script_path_maya = self.cache_sharder_script.replace("\\", "/")
        json_file_maya = json_file.replace("\\", "/")

        maya_command = (
            f'python("json_path = r\'{json_file_maya}\'; '
            f'exec(open(r\'{script_path_maya}\').read())")'
        )

        print("Maya Command:", maya_command)

        try:
            subprocess.Popen([maya_exe, "-command", maya_command])
        except Exception as e:
            QMessageBox.critical(
                self.window,
                "Maya Launch Failed",
                f"Failed to launch Maya:\n{maya_exe}\n\nError: {e}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    sys.exit(app.exec())

