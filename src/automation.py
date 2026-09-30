# automation.py

# Imports da biblioteca padrão
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

# Imports de terceiros (PySide2)
from PySide2.QtCore import QObject, QProcess, Signal, QCoreApplication

class AutomationWorker(QObject):
    log_message = Signal(str)
    task_finished = Signal()
    task_error = Signal(str, str)
    analysis_complete = Signal(dict)

    def __init__(self):
        super(AutomationWorker, self).__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._process_finished)
        self.is_running_log = False

    def _run_command(self, program, args):
        if program.lower() == "svn":
            program = self._get_svn_executable()
            if not program:
                self.task_error.emit(
                    "SVN não encontrado",
                    "Instale o cliente de linha de comando do Subversion (por exemplo, "
                    "TortoiseSVN com 'command line client tools') ou adicione svn.exe ao PATH."
                )
                self.task_finished.emit()
                return
        self.log_message.emit(f"\n> Executando: {program} {' '.join(args)}\n")
        self.is_running_log = False
        self.process.start(program, args)

    def _get_svn_executable(self):
        executable = shutil.which("svn")
        if executable:
            return executable

        program_files = (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        )
        for directory in program_files:
            if not directory:
                continue
            candidate = os.path.join(directory, "TortoiseSVN", "bin", "svn.exe")
            if os.path.isfile(candidate):
                return candidate
        return None
    
    def _handle_stdout(self):
        if not self.is_running_log:
            output = self.process.readAllStandardOutput().data().decode('utf-8', errors='ignore')
            self.log_message.emit(output)

    def _handle_stderr(self):
        output = self.process.readAllStandardError().data().decode('utf-8', errors='ignore')
        self.log_message.emit(output)

    def _process_finished(self):
        if not self.is_running_log:
            self.log_message.emit("\n> Comando finalizado.\n")
            self.task_finished.emit()

    def _run_svn_command_sync(self, args):
        executable = self._get_svn_executable()
        if not executable:
            raise FileNotFoundError(
                "Cliente SVN não encontrado. Instale o cliente de linha de comando "
                "(TortoiseSVN com 'command line client tools') ou adicione svn.exe ao PATH."
            )
        try:
            return subprocess.run(
                [executable] + args,
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=15, check=True
            )
        except FileNotFoundError:
            raise Exception("Comando 'svn' não encontrado. Verifique se as ferramentas de linha de comando do TortoiseSVN estão instaladas e no PATH do sistema.")
        except subprocess.CalledProcessError as e:
            raise Exception(e.stderr.strip() if e.stderr else "Erro desconhecido do SVN.")
        except subprocess.TimeoutExpired:
            raise Exception("Comando excedeu o tempo limite (15s).")

    def analyze_files(self, source_path, files):
        self.is_running_log = True
        self.log_message.emit("> Analisando arquivos no SVN... Isso pode levar um momento.\n")
        all_data = {}
        total_files = len(files)
        
        for i, file in enumerate(files, 1):
            self.log_message.emit(f"  Analisando ({i}/{total_files}): {file}\n")
            QCoreApplication.processEvents()
            
            full_path = os.path.join(source_path, file)
            file_data = {'info': {}, 'logs': []}
            
            try:
                info_result = self._run_svn_command_sync(["info", "--xml", full_path])
                file_data['info'] = self._parse_svn_info_xml(info_result.stdout)
                
                log_result = self._run_svn_command_sync(["log", "--limit", "5", "--xml", full_path])
                file_data['logs'] = self._parse_svn_log_xml(log_result.stdout)

            except Exception as e:
                file_data['error'] = str(e)
                self.log_message.emit(f"  ERRO ao analisar {file}: {e}\n")
            all_data[file] = file_data

        self.log_message.emit("\n> Análise concluída.\n")
        self.analysis_complete.emit(all_data)
        self.is_running_log = False
        self.task_finished.emit()

    def _parse_svn_info_xml(self, xml_string):
        if not xml_string: return {}
        root = ET.fromstring(xml_string)
        entry = root.find('entry')
        if entry is None: return {}
        commit = entry.find('commit')
        return {
            'url': entry.find('url').text if entry.find('url') is not None else '',
            'revision': entry.get('revision'),
            'last_changed_rev': commit.get('revision') if commit is not None else 'N/A',
            'last_changed_author': commit.find('author').text if commit is not None and commit.find('author') is not None else 'N/A'
        }

    def _parse_svn_log_xml(self, xml_string):
        if not xml_string: return []
        root = ET.fromstring(xml_string)
        entries = []
        for logentry in root.findall('logentry'):
            entries.append({
                'revision': logentry.get('revision'),
                'author': logentry.find('author').text if logentry.find('author') is not None else "N/A",
                'date': (logentry.find('date').text or "").split('T')[0],
                'msg': logentry.find('msg').text if logentry.find('msg') is not None else ""
            })
        return entries

    def _get_complementary_filename(self, filename):
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        complement_map = {
            '.sct': '.scx', '.scx': '.sct', '.vct': '.vcx', '.vcx': '.vct',
            '.frt': '.frx', '.frx': '.frt', '.lbt': '.lbx', '.lbx': '.lbt'
        }
        if ext in complement_map:
            return name + complement_map[ext]
        return None

    def download_revision(self, file_data, revision, download_dir):
        info = file_data.get('info', {})
        file_url = info.get('url')
        if not file_url:
            self.task_error.emit("Erro de Download", "Não foi possível encontrar a URL do arquivo no repositório.")
            self.task_finished.emit()
            return
        if not os.path.isdir(download_dir):
            self.task_error.emit("Erro de Download", f"A pasta de destino para downloads não é válida:\n{download_dir}")
            self.task_finished.emit()
            return

        original_filename = file_url.split('/')[-1]
        download_path = os.path.join(download_dir, original_filename)
        args = ["export", "--force", "-r", revision, f"{file_url}@{revision}", download_path]
        self._run_command("svn", args)

        complement_filename = self._get_complementary_filename(original_filename)
        if complement_filename:
            complement_url = file_url.replace(original_filename, complement_filename)
            complement_path = os.path.join(download_dir, complement_filename)
            complement_args = ["export", "--force", "-r", revision, f"{complement_url}@{revision}", complement_path]
            self._run_command("svn", complement_args)

    def lock_files(self, dest_path, files):
        self._run_command("svn", ["lock"] + [os.path.join(dest_path, f) for f in files])

    def unlock_files(self, dest_path, files):
        self._run_command("svn", ["unlock"] + [os.path.join(dest_path, f) for f in files])

    def commit_files(self, dest_path, files, commit_message):
        if not commit_message:
            self.task_error.emit("Erro de Commit", "A mensagem de commit não pode estar vazia.")
            self.task_finished.emit()
            return
        self._run_command("svn", ["commit", "-m", commit_message] + [os.path.join(dest_path, f) for f in files])
    
    def copy_files(self, source_path, dest_path, files):
        if not os.path.isdir(source_path):
            self.task_error.emit("Erro de Cópia", f"A pasta de Origem não foi encontrada:\n{source_path}")
            self.task_finished.emit()
            return
        self.log_message.emit("> Iniciando cópia de arquivos...\n")
        success_count = 0
        for f in files:
            src = os.path.join(source_path, f)
            dest = os.path.join(dest_path, f)
            if os.path.exists(src):
                try:
                    shutil.copy2(src, dest)
                    self.log_message.emit(f"OK: {f} copiado com sucesso.\n")
                    success_count += 1
                except Exception as e:
                    self.log_message.emit(f"ERRO ao copiar {f}: {e}\n")
            else:
                self.log_message.emit(f"AVISO: Arquivo não encontrado na origem: {src}\n")
        self.log_message.emit(f"\n> Cópia finalizada. {success_count}/{len(files)} arquivos copiados.\n")
        self.task_finished.emit()