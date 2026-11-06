# 从 1.x 迁移到 2.0

2.0 是**结构重构 + 行为修正**，主流程（Nmap XML → 4 张工作表的 XLSX，CLI + GUI）
保持不变。内部 API 有不兼容变更，因此主版本号提升。

## 目录变化

| 1.x | 2.0 |
| --- | --- |
| `nmap_parser/*.py`（根目录平铺） | `src/nmap_parser/*.py` |
| `core.py` | `parser.py` + `workbook.py` + `service.py` + `models.py` |
| `requirements.txt` | `pyproject.toml` 的 `dependencies` / `optional-dependencies` |
| `logo.ico` | `assets/logo.ico` |
| 无 | `tests/`、`docs/`、`.github/workflows/`、`LICENSE`、`CHANGELOG.md` |

`requirements.txt` 已移除，避免与 `pyproject.toml` 出现两份不一致的依赖清单。
`uv.lock` 也不再随源码分发，由维护者按本地工具链生成。

## 安装

```bash
pip install .              # 仅 CLI（只装 xlsxwriter）
pip install ".[gui]"       # 需要桌面 GUI
pipx install .             # 隔离安装，推荐
```

`customtkinter` 不再是必需依赖。原先只跑 CLI 的服务器/CI 现在不会拉取 Tk 相关包。

## 命令行

```bash
nmap-parser scan.xml report.xlsx          # 不变
nmap-parser ./scans report.xlsx -r        # 不变
nmap-parser-gui                           # 不变
```

变化：

- `-v/--version` 现在读取包元数据，不再硬编码 `1.0.0`。
- 新增 `--fail-fast`、`--strict`、`--no-summary`、`--log-level`、`-q`。
- 退出码更精确：`0` 全部成功、`1` 部分文件失败但报告已生成、`2` 致命错误
  （输入无效 / 全部失败 / 无法写文件）。1.x 在解析失败时仍返回 `0`。
- 所有输入都解析失败时**不再生成一个空报告**，而是报错退出。
- `python -m nmap_parser` 现在始终进入 CLI；无参数打印帮助，而不是尝试打开
  GUI 窗口。桌面界面请用 `nmap-parser-gui`。
- 输出路径的父目录会自动创建；`.xlsx` 后缀仍会自动补全。

## Python API

旧代码可以继续运行（会收到 `DeprecationWarning`）：

```python
from nmap_parser import NmapConverter

converter = NmapConverter()
data = converter.parse_nmap_xml("scan.xml")
converter.write_to_xlsx(data, "report.xlsx")
```

推荐的新写法：

```python
from nmap_parser import ConversionService

outcome = ConversionService().convert("scan.xml", "report.xlsx", recursive=False)
print(outcome.stats.hosts_total, outcome.stats.ports_open)
for failure in outcome.failures:
    print(failure.path, failure.message)
```

需要更细的控制时：

```python
from nmap_parser import NmapParser, ScanDataset, discover_xml_files, write_report

parser = NmapParser()
dataset = ScanDataset()
for path in discover_xml_files("./scans", recursive=True):
    dataset.extend(parser.parse(path))
write_report(dataset, "report.xlsx")
```

返回值不再是裸字典，而是带类型的 `ScanResult` / `ScanDataset`；漏洞列表从
`vulns` 更名为 `findings`，并且每条记录保留 `elements` 原始 NSE 键值对。

## 报告内容变化

- CPE 列终于有值（1.x 在 `<port>` 下找 CPE，而实际位置是 `<service>` 内）。
- IP 列优先取 IPv4/IPv6，不会再把 MAC 写进去；多个主机名、多个 CPE 用 `; ` 拼接。
- 重复的 NSE `<elem key="cve">` 不再互相覆盖，嵌套 `<table>` 中的 `elem` 也会收集；
  `state`→`result`、`ids`→`cve` 做别名归一化。
- 新增 host-level 脚本（`<hostscript>`）与 pre/post 脚本的记录。
- 端口、主机数、TTL、耗时等写成真正的 Excel 数字；表头冻结、加了自动筛选和
  严重程度高亮。
- 全部文本按字面写入，扫描结果中形如 `=HYPERLINK(...)` 的字符串不会再变成公式。

## 安全与依赖

- `nmap -oX` 输出自带的 `<!DOCTYPE nmaprun>` 默认放行（2.0.0 曾误拒，见
  2.0.1 修复）；只拦截 `<!ENTITY>` 声明与 DTD 内部子集。`NmapParser(allow_dtd=True)`
  仅用于对完全可信的文件放开这两项检查，`max_bytes` 可限制输入体积。
- 最低 Python 版本从 3.8 提升到 3.9。
