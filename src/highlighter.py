# highlighter.py

# Imports de terceiros (PySide2)
from PySide2.QtCore import QRegularExpression
from PySide2.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

class PacoteHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(PacoteHighlighter, self).__init__(parent)
        self.highlighting_rules = []
        
        sol_format = QTextCharFormat(); sol_format.setForeground(QColor("#6da0e0")); sol_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegularExpression(r'\bSol\s*\d+\b'), sol_format))
        
        tf_format = QTextCharFormat(); tf_format.setForeground(QColor("#7bc98d")); tf_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegularExpression(r'\bTF\s*\d+\b'), tf_format))
        
        tkt_format = QTextCharFormat(); tkt_format.setForeground(QColor("#00fcef")); tkt_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegularExpression(r'\bTkt\s*\d+\b'), tkt_format))
        
        date_format = QTextCharFormat(); date_format.setForeground(QColor("#d19a66"))
        self.highlighting_rules.append((QRegularExpression(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'), date_format))
        
        operator_format = QTextCharFormat(); operator_format.setForeground(QColor("#56b6c2"))
        self.highlighting_rules.append((QRegularExpression(r'[&/:]'), operator_format))
        
        component_format = QTextCharFormat(); component_format.setForeground(QColor("#e08de0")); component_format.setFontWeight(QFont.Bold)
        pattern = QRegularExpression(r'\b(?!Sol\b|TF\b|Tkt\b)[\p{L}_][\p{L}\p{N}_]*\b')
        self.highlighting_rules.append((pattern, component_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)