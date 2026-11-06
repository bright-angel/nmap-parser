# nmap-parser · Nmap XML → Excel 报告

[![CI](https://github.com/bright-angel/nmap-parser/actions/workflows/ci.yml/badge.svg)](https://github.com/bright-angel/nmap-parser/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

把 Nmap 扫描的 XML 结果转换成带格式的 Excel 报告，支持命令行与图形界面。
2.0 起采用标准 `src/` 项目结构，核心逻辑分层、类型化，并补齐测试与 CI。

## 功能

- 单文件 / 目录批量转换，支持递归扫描与大小写无关的 `.xml` 匹配
- 生成 4 张工作表：任务信息、主机状态、端口服务、漏洞情况
- CLI 与 GUI 共用同一条转换流水线，错误统计与退出码一致
- 完整解析 NSE 脚本（CVE、严重程度、解决方案、嵌套 table）
- 报告带冻结表头、自动筛选、数值列、严重程度高亮
- 安全加固：拦截实体展开 / XXE、防止 Excel 公式注入、限制超大文件
- CLI 无 GUI 依赖，可在服务器 / CI 中直接使用
- 可选打包为独立 Windows EXE

## 项目结构

```
nmap-parser/
├── src/nmap_parser/
│   ├── __about__.py       # 版本单一来源
│   ├── models.py          # dataclass 数据模型与统计
│   ├── discovery.py       # 输入发现与校验
│   ├── parser.py          # Nmap XML 解析
│   ├── workbook.py        # 表定义驱动的 XLSX 输出
│   ├── service.py         # 转换编排、进度事件
│   ├── cli.py             # 命令行
│   ├── gui.py             # 图形界面（可选依赖）
│   ├── compat.py          # 1.x 兼容门面（已弃用）
│   └── exceptions.py      # 异常层次
├── tests/                 # pytest 用例 + XML 样例
├── docs/                  # 架构、迁移、打包文档
├── assets/logo.ico
├── scripts/gui_launcher.py# PyInstaller 入口
├── .github/workflows/ci.yml
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

分层设计见 [docs/architecture.md](docs/architecture.md)。

## 安装

```bash
pip install .              # 仅 CLI，只依赖 xlsxwriter
pip install ".[gui]"       # 同时安装桌面界面依赖
pipx install .             # 推荐：隔离环境
pip install -e ".[dev]"    # 开发模式（含测试 / lint / 类型检查）
```

要求 Python 3.9+。**注意**：`customtkinter` 现在是可选依赖，只跑 CLI 不再需要它。

## 使用

### 命令行

```bash
nmap-parser scan.xml report.xlsx
nmap-parser ./nmap_scans report.xlsx -r
nmap-parser ./nmap_scans report.xlsx -r --fail-fast
nmap-parser --version
```

| 参数 | 说明 |
| --- | --- |
| `input` | XML 文件或包含 XML 的目录 |
| `output` | 输出 `.xlsx` 路径（缺后缀自动补全，父目录自动创建） |
| `-r, --recursive` | 递归查找子目录 |
| `-q, --quiet` | 静默，只保留错误 |
| `--log-level` | `debug` / `info` / `warning` / `error` / `quiet` |
| `--fail-fast` | 遇到第一个损坏文件即中止，不生成报告 |
| `--strict` | 任意单文件失败都视为致命错误（退出码 2） |
| `--no-summary` | 不打印统计信息 |
| `-v, --version` | 显示版本 |

退出码：`0` 全部成功 · `1` 报告已生成但有文件失败 · `2` 致命错误（输入无效、
全部文件失败、无法写入）。便于在 CI 中判定结果。

`python -m nmap_parser` 等价于 CLI；无参数时打印帮助，不会尝试打开窗口。

### 图形界面

```bash
nmap-parser-gui
# 或从源码
python -m nmap_parser.gui
```

界面支持选择单个 XML 或整个目录、递归选项、实时进度与详细日志。后台线程只负责
计算，界面更新统一回到主线程，避免 1.x 中的线程不安全操作。

### Python API

```python
from nmap_parser import ConversionService

outcome = ConversionService().convert("./scans", "report.xlsx", recursive=True)
print(outcome.stats)
for failure in outcome.failures:
    print(failure.path, failure.message)
```

更细粒度的用法：

```python
from nmap_parser import NmapParser, ScanDataset, discover_xml_files, write_report

dataset = ScanDataset()
parser = NmapParser()
for path in discover_xml_files("./scans", recursive=True):
    dataset.extend(parser.parse(path))
write_report(dataset, "report.xlsx")
```

1.x 的 `NmapConverter` 仍可使用，但会发出 `DeprecationWarning`。迁移说明见
[docs/migration.md](docs/migration.md)。

## 扫描并生成报告

```bash
nmap -sV --script vuln -oX scan.xml 192.168.1.0/24
nmap-parser scan.xml vulnerability_report.xlsx
```

## 输出报告结构

| 工作表 | 主要内容 |
| --- | --- |
| **Task Info** | 扫描工具、版本、参数、开始/结束时间、主机统计、耗时、退出状态 |
| **Host Status** | IP、主机名、up/down、状态原因、TTL、起止时间 |
| **Port & Service** | 端口、协议、状态、服务名/产品/版本、探测方法、可信度、CPE |
| **Vulnerabilities** | NSE 脚本 ID / 输出 / 版本、结果、严重程度、描述、风险、参考链接、解决方案、CVE、BID、CERT、MSF、OSVDB |

CPE 取自 `<service>`（1.x 取错位置导致该列始终为空）；重复的 CVE、嵌套
`<table>` 中的 `elem`、`<hostscript>` 与 pre/post 脚本都会被收录。

## 安全说明

扫描结果中的服务横幅、主机名、脚本输出都来自被扫描主机，属于不可信数据：

- 所有单元格以字符串写入，工作簿关闭公式与 URL 自动识别，`=CMD(...)` 之类的
  内容不会变成可执行公式；
- Nmap `-oX` 输出自带的 `<!DOCTYPE nmaprun>` 与 `<?xml-stylesheet?>` 属于正常内容，
  默认允许；只拒绝含 `<!ENTITY>` 声明或 DTD 内部子集（`<!DOCTYPE ... [ ... ]>`）的
  文档，避免 XXE 与实体展开型 DoS；
- `NmapParser(max_bytes=...)` 可限制输入体积；
- 超长文本按 Excel 单元格上限截断。

处理来自公网的扫描文件时，仍建议先确认文件来源与体积。

## 开发

```bash
pytest                    # 单元 / 集成测试
ruff check . && ruff format --check .
mypy
python -m build           # wheel + sdist
```

新增报告列的步骤、代码约定见 [CONTRIBUTING.md](CONTRIBUTING.md)；
打包 EXE 见 [docs/packaging.md](docs/packaging.md)。

## 常见问题

**GUI 提示不可用？**
`pip install "nmap-xml2xlsx[gui]"` 安装可选依赖。

**转换后报告为空？**
确认输入是有效的 Nmap XML（根元素为 `<nmaprun>`）。损坏文件会在日志与
`outcome.failures` 中列出；若全部损坏则不会生成报告。

**支持其他扫描器的 XML 吗？**
目前只支持 Nmap 格式；可实现同接口解析器并注入 `ConversionService(parser=...)`。

## 许可证

[MIT](LICENSE) · 作者 test233 · 致谢 [Nmap](https://nmap.org/)、
[XlsxWriter](https://github.com/jmcnamara/XlsxWriter)、
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)。
