# automation.py

# Imports da biblioteca padrão
import os
import shutil
import stat
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

    def _process_finished(self, exit_code, exit_status):
        if not self.is_running_log:
            self.log_message.emit("\n> Comando finalizado.\n")
            if exit_code != 0:
                self.task_error.emit(
                    "Erro no SVN",
                    f"O comando SVN terminou com código {exit_code}. Consulte o log para mais detalhes."
                )
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

    @staticmethod
    def _paths_with_actual_case(directory, filenames):
        entries = os.listdir(directory)
        entries_by_casefold = {}
        for entry in entries:
            entries_by_casefold.setdefault(entry.casefold(), []).append(entry)

        paths = []
        for filename in filenames:
            matches = entries_by_casefold.get(filename.casefold(), [])
            if filename in entries:
                actual_filename = filename
            elif len(matches) == 1:
                actual_filename = matches[0]
            elif len(matches) > 1:
                raise ValueError(
                    f"Nome de arquivo ambíguo em '{directory}': {filename}"
                )
            else:
                actual_filename = filename
            paths.append(os.path.join(directory, actual_filename))
        return paths

    def _get_paths_for_action(self, directory, filenames):
        try:
            return self._paths_with_actual_case(directory, filenames)
        except (OSError, ValueError) as e:
            self.task_error.emit("Erro ao localizar arquivos", str(e))
            self.task_finished.emit()
            return None

    @staticmethod
    def _copy_file_preserving_source_attributes(source, destination):
        destination_mode = None
        try:
            if os.path.exists(destination):
                destination_mode = os.stat(destination).st_mode
                if not destination_mode & stat.S_IWRITE:
                    os.chmod(destination, destination_mode | stat.S_IWRITE)
            shutil.copy2(source, destination)
        except OSError as copy_error:
            if destination_mode is not None:
                try:
                    os.chmod(destination, destination_mode)
                except OSError as restore_error:
                    raise OSError(
                        f"{copy_error}; também não foi possível restaurar "
                        f"as permissões anteriores do destino: {restore_error}"
                    ) from copy_error
            raise

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
        try:
            status_result = self._run_svn_command_sync([
                "status", "--xml", "--verbose", "--depth", "immediates", dest_path
            ])
            root = ET.fromstring(status_result.stdout)
        except Exception as e:
            self.task_error.emit(
                "Erro ao verificar arquivos no SVN",
                f"Não foi possível consultar o working copy de destino:\n{e}"
            )
            self.task_finished.emit()
            return

        entries_by_name = {}
        for entry in root.findall(".//entry"):
            entry_path = entry.get("path")
            wc_status = entry.find("wc-status")
            if not entry_path or wc_status is None:
                continue
            item_status = wc_status.get("item", "")

            full_path = entry_path
            if not os.path.isabs(full_path):
                full_path = os.path.join(dest_path, full_path)
            filename = os.path.basename(full_path)
            entries_by_name.setdefault(filename.casefold(), []).append(
                (full_path, item_status)
            )

        paths = []
        missing_files = []
        ambiguous_files = []
        not_lockable_files = []
        new_files = []
        for filename in files:
            matches = entries_by_name.get(filename.casefold(), [])
            if len(matches) == 1:
                path, item_status = matches[0]
                if item_status in {"unversioned", "added"}:
                    new_files.append((filename, item_status))
                elif item_status in {"normal", "modified", "conflicted"}:
                    paths.append(path)
                else:
                    not_lockable_files.append((filename, item_status or "desconhecido"))
            elif len(matches) > 1:
                ambiguous_files.append(filename)
            else:
                missing_files.append(filename)

        if ambiguous_files or not_lockable_files:
            details = []
            if ambiguous_files:
                details.append(
                    "Nome ambíguo no working copy por diferença apenas de "
                    "maiúsculas/minúsculas:\n"
                    + "\n".join(ambiguous_files)
                )
            if not_lockable_files:
                details.append(
                    "Estado SVN incompatível com lock (arquivo: estado):\n"
                    + "\n".join(
                        f"{filename}: {status}"
                        for filename, status in not_lockable_files
                    )
                )
            self.task_error.emit(
                "Arquivos não localizados no working copy",
                "O SVN não pode bloquear todos os arquivos selecionados. "
                "Confira os itens abaixo no diretório de destino:\n\n"
                + "\n\n".join(details)
            )
            self.task_finished.emit()
            return

        if missing_files:
            new_files.extend((filename, "ainda não existe no destino") for filename in missing_files)
        if new_files:
            self.log_message.emit(
                "> Arquivos novos/pendentes ignorados no lock. Copie-os para o "
                "destino e depois faça o Add e defina svn:needs-lock manualmente "
                "no TortoiseSVN antes do commit:\n"
                + "".join(
                    f"  {filename} (status: {status})\n"
                    for filename, status in new_files
                )
            )
        if paths:
            self._run_command("svn", ["lock"] + paths)
        else:
            self.log_message.emit(
                "> Nenhum arquivo versionado selecionado para lock.\n"
            )
            self.task_finished.emit()

    def unlock_files(self, dest_path, files):
        paths = self._get_paths_for_action(dest_path, files)
        if paths is not None:
            self._run_command("svn", ["unlock"] + paths)

    def commit_files(self, dest_path, files, commit_message):
        if not commit_message:
            self.task_error.emit("Erro de Commit", "A mensagem de commit não pode estar vazia.")
            self.task_finished.emit()
            return
        paths = self._get_paths_for_action(dest_path, files)
        if paths is not None:
            self._run_command("svn", ["commit", "-m", commit_message] + paths)
    
    def copy_files(self, source_path, dest_path, files):
        if not os.path.isdir(source_path):
            self.task_error.emit("Erro de Cópia", f"A pasta de Origem não foi encontrada:\n{source_path}")
            self.task_finished.emit()
            return
        source_paths = self._get_paths_for_action(source_path, files)
        if source_paths is None:
            return
        destination_filenames = [os.path.basename(path) for path in source_paths]
        destination_paths = self._get_paths_for_action(dest_path, destination_filenames)
        if destination_paths is None:
            return

        self.log_message.emit("> Iniciando cópia de arquivos...\n")
        success_count = 0
        for f, src, dest in zip(files, source_paths, destination_paths):
            if os.path.exists(src):
                try:
                    self._copy_file_preserving_source_attributes(src, dest)
                    self.log_message.emit(f"OK: {f} copiado com sucesso.\n")
                    success_count += 1
                except PermissionError as e:
                    try:
                        destination_is_read_only = not (
                            os.stat(dest).st_mode & stat.S_IWRITE
                        )
                    except OSError:
                        destination_is_read_only = False

                    if destination_is_read_only:
                        reason = (
                            "O arquivo de destino está marcado como somente leitura. "
                            "Em working copies SVN, confirme que o lock foi concedido "
                            "para esse arquivo (propriedade svn:needs-lock)."
                        )
                    else:
                        reason = (
                            "O Windows negou a gravação no destino. Verifique as "
                            "permissões da pasta e se o arquivo está aberto ou "
                            "bloqueado por outro programa."
                        )
                    self.log_message.emit(
                        f"ERRO ao copiar {f}: {reason}\n"
                        f"  Detalhe: {e}\n"
                    )
                except OSError as e:
                    self.log_message.emit(f"ERRO ao copiar {f}: {e}\n")
            else:
                self.log_message.emit(f"AVISO: Arquivo não encontrado na origem: {src}\n")
        self.log_message.emit(f"\n> Cópia finalizada. {success_count}/{len(files)} arquivos copiados.\n")
        if success_count != len(files):
            self.task_error.emit(
                "Erro de Cópia",
                f"Somente {success_count} de {len(files)} arquivos foram copiados. Consulte o log para mais detalhes."
            )
        self.task_finished.emit()