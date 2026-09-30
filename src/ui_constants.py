# ui_constants.py

# --- Estilo CSS para o Tema Escuro ---
DARK_STYLESHEET = """
QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
    font-family: Consolas, Courier New, monospace;
    font-size: 11pt;
}
QTextEdit, QPlainTextEdit, QLineEdit, QTreeWidget {
    background-color: #3c3f41;
    border: 1px solid #4f5254;
    border-radius: 4px;
    padding: 8px;
}
QHeaderView::section {
    background-color: #555555;
    padding: 4px;
    border: 1px solid #4f5254;
    font-weight: bold;
}
QPushButton {
    background-color: #555555;
    border: 1px solid #666666;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover { background-color: #6a6a6a; }
QPushButton:pressed { background-color: #4a4a4a; }
QPushButton:disabled { background-color: #404040; color: #888888; }
QTabWidget::pane { border: 1px solid #4f5254; }
QTabBar::tab { background: #4a4a4a; padding: 10px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #555555; }
QLabel { font-weight: bold; }
QScrollBar:vertical { border: none; background: #2b2b2b; width: 12px; }
QScrollBar::handle:vertical { background: #555555; min-height: 20px; border-radius: 6px; }
QScrollBar:horizontal { border: none; background: #2b2b2b; height: 12px; }
QScrollBar::handle:horizontal { background: #555555; min-width: 20px; border-radius: 6px; }
"""

# --- Constantes e Mapas ---
PREFIX_MAP = {
    'frm': ('.sct', '.scx'),
    'relpd': ('.frt', '.frx'),
    'frx': ('.frt', '.frx'),
    'boleta': ('.frt', '.frx'),
    'lbl': ('.lbt', '.lbx')
}
CLASS_EXTENSIONS = ('.vct', '.vcx')