#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import json
import time

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.plugin.debug=false;kf.kio.core.warning=false"

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

UNDO_FILE = ".kambios_undo.json"


class KambiosGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KAMBIOS - con Vista Previa y Deshacer")
        self.resize(750, 650)
        self.folder_path = ""
        self.rename_plan = []
        self.undo_available = False

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Selección de carpeta
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Carpeta:")
        self.folder_line = QLineEdit()
        self.folder_button = QPushButton("Seleccionar")
        self.folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_line)
        folder_layout.addWidget(self.folder_button)
        layout.addLayout(folder_layout)

        # Vista previa de archivos actuales
        self.preview_label = QLabel("Archivos actuales:")
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(80)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.preview_text)

        # Botón de deshacer
        self.undo_button = QPushButton("↩️ Deshacer último cambio")
        self.undo_button.setEnabled(False)
        self.undo_button.clicked.connect(self.undo_last_rename)
        layout.addWidget(self.undo_button)

        # Acciones
        layout.addWidget(QLabel("\nAcciones:"))

        # 1. Numerar
        num_group = QGroupBox("1. Numerar archivos")
        num_layout = QHBoxLayout()
        self.num_text = QLineEdit()
        self.num_text.setPlaceholderText("Texto después del número (ej: Factura)")
        self.num_preview_button = QPushButton("Vista previa")
        self.num_preview_button.clicked.connect(self.preview_number)
        num_layout.addWidget(self.num_text)
        num_layout.addWidget(self.num_preview_button)
        num_group.setLayout(num_layout)
        layout.addWidget(num_group)

        # 2. Reemplazar nombre completo
        full_group = QGroupBox("2. Reemplazar nombre completo")
        full_layout = QHBoxLayout()
        self.full_text = QLineEdit()
        self.full_text.setPlaceholderText("Nuevo nombre base (ej: documento)")
        self.full_preview_button = QPushButton("Vista previa")
        self.full_preview_button.clicked.connect(self.preview_full_replace)
        full_layout.addWidget(self.full_text)
        full_layout.addWidget(self.full_preview_button)
        full_group.setLayout(full_layout)
        layout.addWidget(full_group)

        # 3. Reemplazar parte del nombre
        part_group = QGroupBox("3. Reemplazar parte del nombre")
        part_layout = QHBoxLayout()
        self.part_remove = QLineEdit()
        self.part_remove.setPlaceholderText("Texto a quitar")
        self.part_replace = QLineEdit()
        self.part_replace.setPlaceholderText("Texto a poner")
        self.part_preview_button = QPushButton("Vista previa")
        self.part_preview_button.clicked.connect(self.preview_part_replace)
        part_layout.addWidget(self.part_remove)
        part_layout.addWidget(self.part_replace)
        part_layout.addWidget(self.part_preview_button)
        part_group.setLayout(part_layout)
        layout.addWidget(part_group)

        # Tabla de vista previa
        layout.addWidget(QLabel("\nVista previa de cambios:"))
        self.preview_table = QTableWidget(0, 2)
        self.preview_table.setHorizontalHeaderLabels(["Original", "Nuevo"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.preview_table)

        # Botón aplicar
        self.apply_button = QPushButton("✅ Aplicar cambios")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_renames)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta",
            options=QFileDialog.Option.DontUseNativeDialog
        )
        if folder:
            self.folder_path = folder
            self.folder_line.setText(folder)
            self.update_file_list()
            self.check_undo_file()

    def update_file_list(self):
        try:
            files = [f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))]
            self.preview_text.setPlainText(", ".join(files) if files else "(carpeta vacía)")
        except Exception as e:
            self.show_error(f"No se pudo leer la carpeta:\n{str(e)}")

    def check_undo_file(self):
        undo_path = os.path.join(self.folder_path, UNDO_FILE)
        self.undo_available = os.path.exists(undo_path)
        self.undo_button.setEnabled(self.undo_available)

    def show_error(self, message):
        QMessageBox.critical(self, "Error", message)

    def show_info(self, title, message):
        QMessageBox.information(self, title, message)

    def clear_preview(self):
        self.rename_plan = []
        self.preview_table.setRowCount(0)
        self.apply_button.setEnabled(False)

    def validate_and_show_preview(self, changes):
        if not changes:
            self.show_info("Sin cambios", "No se detectaron cambios que aplicar.")
            self.clear_preview()
            return

        new_names = [new for _, new in changes]
        if len(new_names) != len(set(new_names)):
            self.show_error("¡Error! Los nombres nuevos generan duplicados.\nNo se pueden aplicar estos cambios.")
            self.clear_preview()
            return

        self.rename_plan = changes
        self.preview_table.setRowCount(len(changes))
        for row, (old, new) in enumerate(changes):
            self.preview_table.setItem(row, 0, QTableWidgetItem(old))
            self.preview_table.setItem(row, 1, QTableWidgetItem(new))
        self.apply_button.setEnabled(True)

    # Vista previa

    def preview_number(self):
        if not self.folder_path:
            self.show_error("Selecciona una carpeta primero.")
            return
        text = self.num_text.text().strip()
        if not text:
            self.show_error("Ingresa el texto después del número.")
            return

        try:
            files = [f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))]
            changes = []
            for count, filename in enumerate(files):
                _, ext = os.path.splitext(filename)
                new_name = f"{count} - {text}{ext}"
                if filename != new_name:
                    changes.append((filename, new_name))
            self.validate_and_show_preview(changes)
        except Exception as e:
            self.show_error(f"Error al generar vista previa:\n{str(e)}")

    def preview_full_replace(self):
        if not self.folder_path:
            self.show_error("Selecciona una carpeta primero.")
            return
        text = self.full_text.text().strip()
        if not text:
            self.show_error("Ingresa el nuevo nombre base.")
            return

        try:
            files = [f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))]
            changes = []
            for filename in files:
                _, ext = os.path.splitext(filename)
                new_name = f"{text}{ext}"
                if filename != new_name:
                    changes.append((filename, new_name))
            self.validate_and_show_preview(changes)
        except Exception as e:
            self.show_error(f"Error al generar vista previa:\n{str(e)}")

    def preview_part_replace(self):
        if not self.folder_path:
            self.show_error("Selecciona una carpeta primero.")
            return
        text_remove = self.part_remove.text()
        text_replace = self.part_replace.text()
        if not text_remove:
            self.show_error("Ingresa el texto que deseas quitar.")
            return

        try:
            files = [f for f in os.listdir(self.folder_path) if os.path.isfile(os.path.join(self.folder_path, f))]
            changes = []
            for filename in files:
                if text_remove in filename:
                    new_name = filename.replace(text_remove, text_replace)
                    if filename != new_name:
                        changes.append((filename, new_name))
            self.validate_and_show_preview(changes)
        except Exception as e:
            self.show_error(f"Error al generar vista previa:\n{str(e)}")

    # Aplicar y deshacer

    def apply_renames(self):
        if not self.rename_plan:
            return

        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Renombrar {len(self.rename_plan)} archivo(s)?\nEsta acción no se puede deshacer... O quizás sí 😎",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for old_name, new_name in self.rename_plan:
                    src = os.path.join(self.folder_path, old_name)
                    dst = os.path.join(self.folder_path, new_name)
                    os.rename(src, dst)

                undo_path = os.path.join(self.folder_path, UNDO_FILE)
                undo_data = {
                    "timestamp": time.time(),
                    "renames": [[new_name, old_name] for old_name, new_name in self.rename_plan]
                }
                with open(undo_path, "w", encoding="utf-8") as f:
                    json.dump(undo_data, f, indent=2, ensure_ascii=False)

                self.show_info("Éxito", "Archivos renombrados. Puedes deshacer desde esta carpeta.")
                self.update_file_list()
                self.clear_preview()
                self.check_undo_file()

            except Exception as e:
                self.show_error(f"Error al aplicar cambios:\n{str(e)}")

    def undo_last_rename(self):
        undo_path = os.path.join(self.folder_path, UNDO_FILE)
        if not os.path.exists(undo_path):
            self.show_error("No hay operación previa para deshacer.")
            return

        try:
            with open(undo_path, "r", encoding="utf-8") as f:
                undo_data = json.load(f)

            renames = undo_data.get("renames", [])
            if not renames:
                raise ValueError("Archivo de deshacer vacío.")

            reply = QMessageBox.question(
                self,
                "¿Deshacer?",
                f"¿Deshacer el último cambio? ({len(renames)} archivo(s))",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            for current_name, original_name in renames:
                src = os.path.join(self.folder_path, current_name)
                dst = os.path.join(self.folder_path, original_name)
                if os.path.exists(src):
                    os.rename(src, dst)
                else:
                    self.show_error(f"Archivo faltante: {current_name}. La operación puede estar incompleta.")
                    return

            os.remove(undo_path)
            self.show_info("Deshacer", "¡Cambios revertidos correctamente!")
            self.update_file_list()
            self.undo_button.setEnabled(False)

        except Exception as e:
            self.show_error(f"Error al deshacer:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = KambiosGUI()
    window.show()
    sys.exit(app.exec())

