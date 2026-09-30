# main.py

# 1. Imports da biblioteca padrão
import os
import re
import sys
from datetime import datetime

# 2. Imports de terceiros (PySide2)
from PySide2.QtCore import Qt, QRegularExpression, Signal
from PySide2.QtGui import QColor, QFont, QTextCursor
from PySide2.QtWidgets import (
    QApplication, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QTabWidget,
    QTextEdit, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
)

# 3. Imports da aplicação local
from automation import AutomationWorker
from highlighter import PacoteHighlighter
from ui_constants import CLASS_EXTENSIONS, DARK_STYLESHEET, PREFIX_MAP


class LogViewerDialog(QDialog):
    revision_download_requested = Signal(str)

    def __init__(self, filename, log_entries, parent=None):
        super(LogViewerDialog, self).__init__(parent)
        self.setWindowTitle(f"Histórico de Log: {filename}")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        revisions_list_widget = QWidget()
        revisions_layout = QVBoxLayout(revisions_list_widget)
        revisions_layout.addWidget(QLabel("Revisões:"))
        self.revisions_list = QListWidget()
        self.revisions_list.currentItemChanged.connect(self.update_details_view)
        revisions_layout.addWidget(self.revisions_list)
        splitter.addWidget(revisions_list_widget)

        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.addWidget(QLabel("Detalhes do Commit:"))
        self.commit_details_view = QTextEdit()
        self.commit_details_view.setReadOnly(True)
        self.commit_details_view.setFont(QFont("Consolas", 11))
        details_layout.addWidget(self.commit_details_view)
        splitter.addWidget(details_widget)
        
        splitter.setSizes([250, 550])

        self.download_button = QPushButton("Baixar Revisão Selecionada (e seu complemento)")
        self.download_button.setEnabled(False)
        self.download_button.setFixedHeight(40)
        self.download_button.clicked.connect(self.on_download_clicked)
        main_layout.addWidget(self.download_button)

        self.populate_revisions_list(log_entries)
        if self.revisions_list.count() > 0:
            self.revisions_list.setCurrentRow(0)

    def populate_revisions_list(self, log_entries):
        if not log_entries:
            self.revisions_list.addItem("Nenhum histórico encontrado.")
            return

        for entry in log_entries:
            item_text = f"r{entry['revision']} | {entry['date']}"
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.UserRole, entry)
            self.revisions_list.addItem(list_item)

    def update_details_view(self, current_item, previous_item):
        if not current_item:
            self.commit_details_view.clear()
            self.download_button.setEnabled(False)
            return

        entry = current_item.data(Qt.UserRole)
        if not entry: return

        details_text = (
            f"Revisão:\t{entry.get('revision', 'N/A')}\n"
            f"Autor:\t\t{entry.get('author', 'N/A')}\n"
            f"Data:\t\t{entry.get('date', 'N/A')}\n"
            f"--------------------------------------------------\n\n"
            f"{entry.get('msg', '(sem mensagem)')}"
        )
        self.commit_details_view.setText(details_text)
        self.download_button.setEnabled(True)

    def on_download_clicked(self):
        current_item = self.revisions_list.currentItem()
        if not current_item: return

        entry = current_item.data(Qt.UserRole)
        if entry and 'revision' in entry:
            self.revision_download_requested.emit(entry['revision'])
            self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Assistente de Release Guardian")
        self.setGeometry(100, 100, 900, 900)

        self.automation_worker = AutomationWorker()
        self.automation_worker.log_message.connect(self.append_to_log)
        self.automation_worker.task_finished.connect(self.on_task_finished)
        self.automation_worker.task_error.connect(self.show_error_message)
        self.automation_worker.analysis_complete.connect(self.populate_files_table)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.create_tab_gerador_pacote()
        self.create_tab_automacao()

    def create_tab_gerador_pacote(self):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Cole ou digite aqui os componentes do pacote de release...")
        layout.addWidget(self.editor)
        self.generate_button = QPushButton("Gerar Arquivo de Pacote")
        self.generate_button.setFixedHeight(40)
        self.generate_button.clicked.connect(self.generate_release_file)
        layout.addWidget(self.generate_button)
        self.highlighter = PacoteHighlighter(self.editor.document())
        self.tabs.addTab(tab_widget, "1. Criar Pacote de Release")

    def create_tab_automacao(self):
        tab_widget = QScrollArea()
        tab_widget.setWidgetResizable(True)
        tab_content = QWidget()
        layout = QGridLayout(tab_content)
        
        layout.addWidget(QLabel("1. Selecione o Arquivo de Pacote:"), 0, 0, 1, 3)
        self.package_file_path = QLineEdit(); self.package_file_path.setReadOnly(True)
        layout.addWidget(self.package_file_path, 1, 0, 1, 2)
        self.select_package_button = QPushButton("Selecionar Arquivo...")
        self.select_package_button.clicked.connect(self.select_package_file)
        layout.addWidget(self.select_package_button, 1, 2)
        
        layout.addWidget(QLabel("2. Pasta Principal do Projeto (para buscar logs):"), 2, 0, 1, 3)
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("Ex: D:\\Projetos\\SistemaPrincipal\\CFSW")
        layout.addWidget(self.source_path_input, 3, 0, 1, 3)
        
        layout.addWidget(QLabel("3. Pasta de Destino para Downloads (Revisão Específica):"), 4, 0, 1, 2)
        self.download_path_input = QLineEdit()
        self.download_path_input.setPlaceholderText("Ex: C:\\Users\\SeuUsuario\\Downloads\\Revisoes")
        layout.addWidget(self.download_path_input, 5, 0, 1, 2)
        self.select_download_path_button = QPushButton("Procurar...")
        self.select_download_path_button.clicked.connect(self.select_download_folder)
        layout.addWidget(self.select_download_path_button, 5, 2)

        self.fetch_logs_button = QPushButton("4. Analisar Arquivos (svn info & log)")
        self.fetch_logs_button.clicked.connect(self.run_analyze_files)
        layout.addWidget(self.fetch_logs_button, 6, 0, 1, 3)
        
        table_label = QLabel("5. Selecione os arquivos para liberar (dê um duplo-clique para ver o log):")
        layout.addWidget(table_label, 7, 0)
        check_buttons_layout = QHBoxLayout()
        self.check_all_button = QPushButton("Marcar Todos")
        self.check_all_button.clicked.connect(self.check_all_files)
        self.uncheck_all_button = QPushButton("Desmarcar Todos")
        self.uncheck_all_button.clicked.connect(self.uncheck_all_files)
        check_buttons_layout.addStretch()
        check_buttons_layout.addWidget(self.check_all_button)
        check_buttons_layout.addWidget(self.uncheck_all_button)
        layout.addLayout(check_buttons_layout, 7, 1, 1, 2)
        
        self.files_table = QTableWidget()
        self.files_table.setMinimumSize(480, 220)
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["", "Componente", "Revisão Atual", "Último Autor"])
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.setColumnWidth(0, 40)
        self.files_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.files_table.itemDoubleClicked.connect(self.show_log_viewer)
        layout.addWidget(self.files_table, 8, 0, 1, 3)
        
        layout.addWidget(QLabel("6. Pasta do Release Congelado (Destino/SVN):"), 9, 0, 1, 3)
        self.dest_path_input = QLineEdit()
        self.dest_path_input.setPlaceholderText("Ex: C:\\Releases\\Versao_Congelada\\CFSW")
        layout.addWidget(self.dest_path_input, 10, 0, 1, 3)

        self.lock_button = QPushButton("Passo 7.1: Lockar Selecionados")
        self.lock_button.clicked.connect(self.run_lock_files)
        layout.addWidget(self.lock_button, 11, 0)
        self.copy_button = QPushButton("Passo 7.2: Copiar Selecionados")
        self.copy_button.clicked.connect(self.run_copy_files)
        layout.addWidget(self.copy_button, 11, 1)
        self.commit_button = QPushButton("Passo 7.3: Commit Selecionados")
        self.commit_button.clicked.connect(self.run_commit_files)
        layout.addWidget(self.commit_button, 11, 2)
        layout.addWidget(QLabel("Mensagem do Commit:"), 12, 0, 1, 3)
        self.commit_message_input = QTextEdit(); self.commit_message_input.setFixedHeight(60)
        layout.addWidget(self.commit_message_input, 13, 0, 1, 3)
        self.unlock_button = QPushButton("Passo 7.4: Liberar Locks")
        self.unlock_button.clicked.connect(self.run_unlock_files)
        layout.addWidget(self.unlock_button, 14, 0)
        layout.addWidget(QLabel("Log de Saída:"), 15, 0)
        self.log_output = QPlainTextEdit(); self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        layout.addWidget(self.log_output, 16, 0, 1, 3)
        layout.setRowStretch(8, 3)
        layout.setRowStretch(16, 2)
        tab_widget.setWidget(tab_content)
        self.tabs.addTab(tab_widget, "2. Executar Automação")
        self._set_action_buttons_enabled(False)
        self.check_all_button.setEnabled(False)
        self.uncheck_all_button.setEnabled(False)

    def append_to_log(self, message):
        self.log_output.insertPlainText(message)
        self.log_output.moveCursor(QTextCursor.End)

    def on_task_finished(self):
        self._set_buttons_enabled(True)

    def show_error_message(self, title, message):
        QMessageBox.critical(self, title, message)
        self._set_buttons_enabled(True)

    def _set_buttons_enabled(self, enabled):
        self.fetch_logs_button.setEnabled(enabled)
        has_items_to_action = self.files_table.rowCount() > 0
        self._set_action_buttons_enabled(enabled and has_items_to_action)

    def _set_action_buttons_enabled(self, enabled):
        self.lock_button.setEnabled(enabled)
        self.copy_button.setEnabled(enabled)
        self.commit_button.setEnabled(enabled)
        self.unlock_button.setEnabled(enabled)
        self.check_all_button.setEnabled(enabled)
        self.uncheck_all_button.setEnabled(enabled)

    def check_all_files(self):
        for row in range(self.files_table.rowCount()):
            item = self.files_table.item(row, 0)
            if item: item.setCheckState(Qt.Checked)

    def uncheck_all_files(self):
        for row in range(self.files_table.rowCount()):
            item = self.files_table.item(row, 0)
            if item: item.setCheckState(Qt.Unchecked)

    def generate_release_file(self):
        full_text = self.editor.toPlainText()
        if not full_text.strip():
            QMessageBox.warning(self, "Aviso", "O editor está vazio.")
            return
        arquivos_para_release = set()
        IGNORE_KEYWORDS = ['copia tortoise', 'pacote de atualizações', 'tarefas', 'solicitações', 'tickets']
        lines = full_text.split('\n')
        for line in lines:
            line_clean = line.strip()
            line_lower = line_clean.lower()
            if not line_clean or line_lower.startswith(('sol ', 'tf ', 'tkt ')) or any(keyword in line_lower for keyword in IGNORE_KEYWORDS):
                continue
            potential_components = re.split(r'[\s&]+', line_clean)
            for comp in potential_components:
                if not comp or not (comp[0].isalpha() or comp[0] == '_'):
                    continue
                comp_lower = comp.lower()
                extensoes = None
                for prefix, exts in PREFIX_MAP.items():
                    if comp_lower.startswith(prefix):
                        extensoes = exts
                        break
                if extensoes is None:
                    extensoes = CLASS_EXTENSIONS
                arquivos_para_release.add(f"{comp}{extensoes[0]}")
                arquivos_para_release.add(f"{comp}{extensoes[1]}")
        if not arquivos_para_release:
            QMessageBox.warning(self, "Aviso", "Nenhum componente válido foi encontrado.")
            return
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"pacote_release_{timestamp}.txt"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for arquivo in sorted(list(arquivos_para_release)):
                    f.write(f"{arquivo}\n")
            QMessageBox.information(self, "Sucesso", f"Arquivo de release gerado com sucesso!\nSalvo como: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao salvar o arquivo:\n{e}")

    def select_package_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo de Pacote", "", "Arquivos de Texto (*.txt)")
        if filepath:
            self.package_file_path.setText(filepath)
            self._set_action_buttons_enabled(False)
            self.files_table.setRowCount(0)
    
    def select_download_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Downloads")
        if dir_path:
            self.download_path_input.setText(dir_path)

    def _get_validated_paths_and_files(self, require_dest=True):
        package_file = self.package_file_path.text()
        source_path = self.source_path_input.text()
        dest_path = self.dest_path_input.text()
        required_paths = [package_file, source_path]
        if require_dest:
            required_paths.append(dest_path)
        if not all(path.strip() for path in required_paths):
            QMessageBox.warning(self, "Erro", "Todos os campos de caminho necessários devem ser preenchidos.")
            return None, None, None
        if not os.path.isfile(package_file):
            QMessageBox.critical(self, "Erro", f"Arquivo de pacote não encontrado: {package_file}")
            return None, None, None
        if require_dest and not os.path.isdir(dest_path):
            QMessageBox.critical(self, "Erro", f"Pasta de Destino/SVN não encontrada: {dest_path}")
            return None, None, None
        try:
            with open(package_file, 'r', encoding='utf-8') as f:
                files = [line.strip() for line in f if line.strip()]
            if not files:
                QMessageBox.warning(self, "Erro", "O arquivo de pacote está vazio.")
                return None, None, None
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível ler o arquivo de pacote:\n{e}")
            return None, None, None
        return source_path, dest_path, files

    def run_analyze_files(self):
        source_path, _, files = self._get_validated_paths_and_files(require_dest=False)
        if not files: return
        self.log_output.clear()
        self.files_table.setRowCount(0)
        self._set_buttons_enabled(False)
        self.automation_worker.analyze_files(source_path, files)

    def populate_files_table(self, analysis_data):
        self.files_table.setRowCount(0)
        self.files_table.setRowCount(len(analysis_data))
        for row, (filename, data) in enumerate(analysis_data.items()):
            info = data.get('info', {})
            error = data.get('error')
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            check_item.setCheckState(Qt.Checked)
            file_item = QTableWidgetItem(filename)
            file_item.setData(Qt.UserRole, data)
            rev_item = QTableWidgetItem(info.get('revision', 'N/A'))
            author_item = QTableWidgetItem(info.get('last_changed_author', 'N/A'))
            if error:
                file_item.setText(f"{filename} (ERRO)")
                file_item.setToolTip(error)
                file_item.setForeground(QColor("#ff8080"))
                check_item.setCheckState(Qt.Unchecked)
            self.files_table.setItem(row, 0, check_item)
            self.files_table.setItem(row, 1, file_item)
            self.files_table.setItem(row, 2, rev_item)
            self.files_table.setItem(row, 3, author_item)
        self._set_buttons_enabled(True)

    def show_log_viewer(self, item):
        row = item.row()
        file_item = self.files_table.item(row, 1)
        full_data = file_item.data(Qt.UserRole)
        filename = file_item.text().split(' (ERRO)')[0]
        log_entries = full_data.get('logs')
        if not log_entries:
            QMessageBox.information(self, "Sem Log", f"Não há informações de log para exibir para o arquivo {filename}.")
            return
        dialog = LogViewerDialog(filename, log_entries, self)
        dialog.revision_download_requested.connect(
            lambda rev: self.run_download_revision(full_data, rev)
        )
        dialog.exec_()

    def run_download_revision(self, file_data, revision):
        download_dir = self.download_path_input.text().strip()
        if not download_dir:
            QMessageBox.warning(self, "Aviso", "Por favor, preencha a 'Pasta de Destino para Downloads' antes de baixar uma revisão.")
            return
        self._set_buttons_enabled(False)
        self.log_output.clear()
        self.automation_worker.download_revision(file_data, revision, download_dir)

    def _get_selected_files_from_table(self):
        selected_files = []
        for row in range(self.files_table.rowCount()):
            if self.files_table.item(row, 0).checkState() == Qt.Checked:
                filename = self.files_table.item(row, 1).text().split(' (ERRO)')[0]
                selected_files.append(filename)
        if not selected_files:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo está selecionado na tabela.")
            return None
        return selected_files
        
    def run_lock_files(self):
        _, dest_path, _ = self._get_validated_paths_and_files()
        selected_files = self._get_selected_files_from_table()
        if not dest_path or not selected_files: return
        self._set_buttons_enabled(False)
        self.log_output.clear()
        self.automation_worker.lock_files(dest_path, selected_files)

    def run_copy_files(self):
        source_path, dest_path, _ = self._get_validated_paths_and_files()
        selected_files = self._get_selected_files_from_table()
        if not all([source_path, dest_path, selected_files]): return
        self._set_buttons_enabled(False)
        self.log_output.clear()
        self.automation_worker.copy_files(source_path, dest_path, selected_files)

    def run_commit_files(self):
        _, dest_path, _ = self._get_validated_paths_and_files()
        selected_files = self._get_selected_files_from_table()
        commit_message = self.commit_message_input.toPlainText().strip()
        if not all([dest_path, selected_files]): return
        self._set_buttons_enabled(False)
        self.log_output.clear()
        self.automation_worker.commit_files(dest_path, selected_files, commit_message)

    def run_unlock_files(self):
        _, dest_path, _ = self._get_validated_paths_and_files()
        selected_files = self._get_selected_files_from_table()
        if not dest_path or not selected_files: return
        self._set_buttons_enabled(False)
        self.log_output.clear()
        self.automation_worker.unlock_files(dest_path, selected_files)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())