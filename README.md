# Assistente de Release Guardian (Atualizações Automatizadas)

Este projeto é uma ferramenta de automação desenvolvida em **Python** com interface gráfica em **PySide2 (Qt 5)**. Seu objetivo é simplificar, padronizar e automatizar o processo de liberação/release de componentes legados (com suporte nativo a pares binários do Visual FoxPro, tais como `.scx/.sct`, `.vcx/.v3ct`, `.frx/.frt`, `.lbx/.lbt`) integrados ao **Apache Subversion (SVN)**.

---

## 🛠️ Requisitos do Sistema

* **Python 3.10 64-bit** para gerar o executável
* **Apache Subversion (SVN Client)** via linha de comando (`svn.exe`)

### Dependências Python
Instale as dependências necessárias utilizando o `pip`:

```bash
pip install -r requirements.txt
```

## Gerar o executável no Windows

Instale o Python 3.10 de 64 bits e execute `build_exe.bat` na pasta do projeto. O script prepara o ambiente `.venv-pyside2`, instala as dependências e gera um executável único, sem janela de console, em:

**https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe Segue instalador 3.10

```text
dist/AssistenteReleaseGuardian.exe
```

O executável inclui a aplicação e o PySide2, mas **não inclui o cliente SVN**. O computador onde ele for usado ainda precisa ter `svn.exe` instalado e acessível no `PATH`, conforme a seção de configuração do SVN. O build é x64 e usa Qt 5 para compatibilidade com Windows Server 2012 R2.

---

## ⚙️ Configuração do Ambiente SVN

Para que a automação execute os comandos de histórico, cópia, *lock*, *commit* e *download* de revisões, o executável `svn.exe` **deve estar acessível no PATH do sistema**.

### Como configurar o SVN no Windows

#### Opção A: Via TortoiseSVN (Recomendado)
1. Faça o download do [TortoiseSVN](https://tortoisesvn.net/downloads.html) (versão 64-bit).
2. Durante o processo de instalação, na tela **Custom Setup**, certifique-se de marcar a opção:
   * 🟢 **`Command line client tools`** (Ferramentas do cliente de linha de comando).
3. Conclua a instalação e reinicie o terminal.

> **Nota:** Caso já possua o TortoiseSVN instalado sem essa opção, acesse *Painel de Controle -> Programas e Recursos -> TortoiseSVN -> Alterar (Modify)* e ative a opção `Command line client tools`.

#### Opção B: Via SlikSVN (Cliente Leve de Terminal)
1. Baixe o instalador do [SlikSVN](https://sliksvn.com/download/).
2. Execute a instalação padrão. O `svn.exe` será configurado automaticamente no `PATH`.

### Validando a Instalação
Abra o Prompt de Comando (CMD) ou PowerShell e digite:

```bash
svn --version
```
Se a versão do Subversion for exibida no terminal, o ambiente está pronto para uso pela aplicação.

---

## 📂 Estrutura do Projeto

```text
AtualizacoesGuardianAutomatizadas/
├── README.md               # Documentação do projeto
├── .gitignore              # Padrões ignorados pelo Git
└── src/
   ├── main.py             # Interface gráfica principal e janelas modais (PySide2)
    ├── automation.py       # Lógica do worker e execução de comandos SVN/Subprocess
    ├── highlighter.py      # Destaque de sintaxe (Highlighter) para editor de texto
    └── ui_constants.py     # Estilos CSS (Dark Theme) e mapas de extensões/prefixos
```

---

## 🚀 Como Utilizar a Aplicação

Para iniciar o programa, execute o arquivo `main.py`:

```bash
.venv-pyside2/Scripts/python.exe src/main.py
```

### Fluxo de Trabalho (Workflow):

1. **Aba 1 - Criar Pacote de Release**:
   * Cole o resumo de solicitações, chamados ou tarefas no editor de texto.
   * Clique em **Gerar Arquivo de Pacote**. O sistema identificará automaticamente os componentes e gerará um arquivo `.txt` contendo a lista com as extensões associadas (ex: `.scx` e `.sct`).

2. **Aba 2 - Executar Automação**:
   * **Passo 1**: Selecione o arquivo `.txt` gerado no passo anterior.
   * **Passo 2**: Informe o caminho da pasta principal do projeto (código-fonte em desenvolvimento).
   * **Passo 3**: Informe a pasta de destino para downloads de revisões pontuais.
   * **Passo 4**: Clique em **Analisar Arquivos**. O sistema executará `svn info` e `svn log` para preencher a tabela com a versão e o autor atual.
   * *(Opcional)*: Dê duplo-clique em qualquer linha para abrir o histórico de revisões do arquivo e baixar versões específicas.
   * **Passo 6 & 7**: Informe o caminho do diretório congelado (destino do release/SVN) e utilize a sequência de botões para:
     1. **Lockar Selecionados** (`svn lock`)
     2. **Copiar Selecionados** (Cópia local Origem ➔ Destino)
     3. **Commit Selecionados** (`svn commit` com mensagem)
     4. **Liberar Locks** (`svn unlock`)