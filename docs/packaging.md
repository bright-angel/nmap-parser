# 构建与打包

## 1. 构建 Python 分发包

```bash
pip install build
python -m build           # 生成 dist/*.whl 与 dist/*.tar.gz
python -m pip install dist/*.whl
nmap-parser --version
```

版本号来自 `src/nmap_parser/__about__.py`，`pyproject.toml` 通过
`[tool.setuptools.dynamic]` 动态读取，不需要两处同步修改。

隔离安装（推荐给只想用命令行的用户）：

```bash
pipx install .
nmap-parser scan.xml report.xlsx
```

需要 GUI 时：`pipx install ".[gui]"`。

## 2. 打包为独立 Windows EXE

先安装完整依赖，再执行 PyInstaller：

```bash
pip install -e ".[gui]"
pip install pyinstaller

pyinstaller --onefile --windowed --noconfirm --clean ^
  --name nmap-parser-gui ^
  --icon assets/logo.ico ^
  --hidden-import customtkinter ^
  --hidden-import tkinter ^
  --collect-all customtkinter ^
  scripts/gui_launcher.py
```

Bash / macOS / Linux 下把 `^` 换成 `\`；Linux 与 macOS 无需 `--windowed` 时
可去掉。产物在 `dist/nmap-parser-gui.exe`（约 30–50 MB）。

要点：

- 入口使用 `scripts/gui_launcher.py`，而不是直接指向 `src/nmap_parser/gui.py`，
  这样打包命令不依赖内部目录布局，包内相对导入也能正常解析。
- `--collect-all customtkinter` 必须保留，否则主题与字体资源会缺失。
- 图标路径已改为 `assets/logo.ico`。
- 打包前需先 `pip install` 本项目，否则 `nmap_parser` 不在解析路径上。
- `*.spec`、`build/`、`dist/` 已在 `.gitignore` 中排除。

## 3. 分发前检查

```bash
pytest
ruff check .
mypy
python -m build
```

CI（`.github/workflows/ci.yml`）在 Python 3.9–3.13 × Linux/Windows 上执行同样的
检查，并额外验证构建出来的 wheel 能被安装、`nmap-parser --version` 可执行。
