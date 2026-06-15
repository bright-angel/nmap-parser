# Nmap XML to Excel Converter

将 Nmap 扫描的 XML 结果转换为美观的 Excel 报告工具，支持命令行和图形界面两种使用方式。

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)

## 功能特点

- ✅ **多模式支持**：单个 XML 文件或整个目录批量转换
- ✅ **递归扫描**：支持递归查找子目录中的所有 XML 文件
- ✅ **完整报告**：自动生成 4 个工作表的 Excel 报告
- ✅ **双界面**：命令行 (CLI) 和图形界面 (GUI) 双版本
- ✅ **易于安装**：支持 pipx 隔离安装，无需配置虚拟环境
- ✅ **完整漏洞信息**：解析 Nmap NSE 脚本的详细漏洞数据（CVE、严重程度、解决方案等）
- ✅ **跨平台**：支持 Windows、Linux、macOS
- ✅ **独立 EXE**：可打包为独立 Windows 程序，无需 Python 环境

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装工具

**方式 A：使用 pipx（推荐，隔离环境）**

```bash
pipx install .
```

**方式 B：使用 pip**

```bash
pip install .
```

**方式 C：开发模式**

```bash
pip install -e .
```

### 3. 使用

**命令行模式：**

```bash
nmap-parser scan.xml report.xlsx
```

**图形界面模式：**

```bash
nmap-parser-gui
```

## 安装方式对比

| 方式 | 命令 | 适用场景 |
|------|------|----------|
| **pipx** | `pipx install .` | 推荐使用，独立隔离环境 |
| **pip** | `pip install .` | 系统级安装 |
| **开发** | `pip install -e .` | 开发调试模式 |
| **手动** | `python nmap_parser/gui.py` | 无需安装，直接运行 |

## 使用方法

### 命令行模式 (CLI)

**基础用法：**

```bash
# 转换单个 XML 文件
nmap-parser scan.xml report.xlsx

# 转换目录下所有 XML 文件
nmap-parser ./nmap_scans report.xlsx

# 递归转换（包含子目录）
nmap-parser ./nmap_scans report.xlsx -r

# 静默模式（不输出日志）
nmap-parser scan.xml report.xlsx -q

# 查看版本
nmap-parser -v
```

**命令行参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `input` | - | 输入路径（XML 文件或目录） |
| `output` | - | 输出 Excel 文件路径（.xlsx） |
| `--recursive` | `-r` | 递归查找子目录 |
| `--quiet` | `-q` | 静默模式，不输出日志 |
| `--version` | `-v` | 显示版本信息 |
| `--help` | `-h` | 显示帮助信息 |

**退出码：**

- `0` - 成功
- `1` - 错误（未找到文件、解析失败等）

### 图形界面模式 (GUI)

**启动方式：**

```bash
# 已安装
nmap-parser-gui

# 未安装，直接运行
python nmap_parser/gui.py
```

**界面功能：**

- 📁 **文件选择器**：点击浏览选择输入 XML 文件或目录
- 📂 **目录浏览**：可选择文件夹进行批量转换
- 🔄 **递归选项**：勾选后递归扫描子目录
- 📊 **实时进度**：显示转换进度条
- 📝 **详细日志**：显示每个文件的处理状态
- ✅ **完成提示**：转换完成后弹出对话框

## 输出 Excel 结构

生成的 Excel 包含 4 个工作表：

### 1️⃣ 任务信息 (Task Info)

| 列名 | 说明 |
|------|------|
| xml 文件名 | 扫描的 XML 文件名 |
| 扫描工具 | Nmap 或其他扫描器名称 |
| 工具版本 | 扫描器版本号 |
| 扫描参数 | Nmap 命令行参数 |
| 开始时间戳 | Unix 时间戳格式 |
| 开始时间 | 可读的时间格式 |
| XML 版本 | Nmap XML 输出格式版本 |
| 总主机数 | 扫描的主机总数 |
| 存活主机数 | 在线主机数量 |
| 下线主机数 | 离线主机数量 |
| 结束时间戳 | 扫描结束时间戳 |
| 结束时间 | 可读的结束时间 |
| 耗时 (秒) | 扫描持续时间 |
| 退出状态 | 扫描任务状态（success/fail） |

### 2️⃣ 主机状态 (Host Status)

| 列名 | 说明 |
|------|------|
| xml 文件名 | 来源 XML 文件 |
| IP 地址 | 主机 IP 地址 |
| 主机名 | 反向解析的主机名 |
| 状态 | up/down |
| 状态原因 | 判断状态的依据 |
| 状态 TTL | 响应 TTL 值 |
| 开始时间 | 主机扫描开始时间 |
| 结束时间 | 主机扫描结束时间 |

### 3️⃣ 端口服务 (Port & Service)

| 列名 | 说明 |
|------|------|
| xml 文件名 | 来源 XML 文件 |
| IP 地址 | 主机 IP |
| 端口号 | 端口号 (1-65535) |
| 协议 | TCP/UDP |
| 状态 | open/closed/filtered |
| 状态原因 | 状态判断原因 |
| 状态 TTL | TTL 值 |
| 服务名称 | 识别的服务名 |
| 服务产品 | 产品名（如 OpenSSH） |
| 服务版本 | 版本号 |
| 服务额外信息 | 系统、协议等额外信息 |
| 探测方法 | table/probed |
| 可信度 | 1-10 的置信度 |
| CPE 信息 | 通用平台枚举标识符 |

### 4️⃣ 漏洞情况 (Vulnerabilities)

基于 Nmap NSE 脚本的详细输出：

| 列名 | XML 路径 | 说明 |
|------|---------|------|
| 脚本 ID | `script@id` | NSE 脚本标识符 |
| 输出 | `script@output` | 脚本原始输出 |
| 版本 | `script@version` | 脚本版本 |
| 协议 | `port@protocol` | 端口协议 |
| 结果 | `elem[@key="result"]` | 检测结果 (如 VULNERABLE) |
| 严重程度 | `elem[@key="severity"]` | HIGH/MEDIUM/LOW |
| 描述 | `elem[@key="description"]` | 漏洞详细描述 |
| 风险因素 | `elem[@key="risk_factor"]` | Critical/High/Medium/Low |
| 参考链接 | `elem[@key="see_also"]` | 外部参考链接 |
| 解决方案 | `elem[@key="solution"]` | 修复建议 |
| CVE 编号 | `elem[@key="cve"]` | CVE 标识符 |
| BID 编号 | `elem[@key="bid"]` | BugTraq ID |
| CERT 公告 | `elem[@key="cert"]` | CERT 公告编号 |
| MSF 模块 | `elem[@key="msf_module"]` | Metasploit 模块名 |
| OSVDB 编号 | `elem[@key="osvdb"]` | 开源漏洞库 ID |

## 使用示例

### 示例 1：转换单个扫描文件

```bash
nmap-parser nmap_scan.xml report.xlsx
```

### 示例 2：批量转换目录

```bash
nmap-parser ./scans/ all_reports.xlsx -r
```

### 示例 3：生成带漏洞详情的报告

使用 Nmap 进行漏洞扫描（需要安装 NSE 脚本）：

```bash
# Nmap 扫描并输出 XML
nmap -sV --script vuln -oX scan_result.xml 192.168.1.0/24

# 转换为 Excel
nmap-parser scan_result.xml vulnerability_report.xlsx
```

### 示例 4：在 CI/CD 中使用

```bash
# 扫描
nmap -oX results.xml target.host

# 转换
nmap-parser results.xml report.xlsx

# 检查生成结果
ls -la report.xlsx
```

## 系统要求

### 运行环境

- **Python**: 3.8 或更高版本
- **操作系统**：Windows 7/10/11、Linux、macOS

### 依赖库

```txt
xlsxwriter>=3.0.0      # Excel 文件生成
customtkinter>=5.2.0   # GUI 框架
darkdetect             # 暗色模式检测
packaging              # 工具库
```

## 打包为独立 EXE (Windows)

### 快速打包

```batch
build_exe_simple.bat
```

### 完整打包（带版本信息）

```batch
build_exe.bat
```

### 手动打包

```batch
pip install pyinstaller

pyinstaller --onefile --windowed --name "nmap-parser-gui" --hidden-import customtkinter --hidden-import tkinter --hidden-import xlsxwriter --collect-all customtkinter --noconfirm --clean nmap_parser\gui.py
```

打包成功后，在 `dist` 目录生成独立的 EXE 文件（约 30-50 MB），无需 Python 环境即可运行。

## 项目结构

```
workspace/
├── pyproject.toml         # 项目配置文件
├── requirements.txt       # Python 依赖
├── README.md              # 使用文档
├── PACKAGING.md           # 打包指南
├── build_exe.bat          # Windows 打包脚本（完整版）
├── build_exe_simple.bat   # Windows 打包脚本（简易版）
└── nmap_parser/
    ├── __init__.py        # 包初始化
    ├── core.py            # 核心转换逻辑
    ├── cli.py             # 命令行界面
    └── gui.py             # 图形界面
```

## 开发指南

### 安装开发环境

```bash
pip install -e .
pip install -r requirements.txt
```

### 运行测试

```bash
# 命令行模式
python -m nmap_parser.cli test_scan.xml output.xlsx

# GUI 模式
python -m nmap_parser.gui

# 或直接运行（无需安装）
python nmap_parser/cli.py test_scan.xml output.xlsx
python nmap_parser/gui.py
```

### 代码结构

- **core.py**: NmapConverter 类，包含 XML 解析和 XLSX 生成逻辑
- **cli.py**: 命令行解析，调用核心功能
- **gui.py**: CustomTkinter 实现的图形界面

## 常见问题

### Q: 为什么 GUI 打不开？

确保已安装 customtkinter：

```bash
pip install customtkinter
```

### Q: 转换后 Excel 为空？

检查输入的 XML 文件是否是有效的 Nmap 输出格式。

### Q: 支持其他扫描器的 XML 吗？

当前仅支持 Nmap XML 格式，其他扫描器需要适配 XML 解析逻辑。

### Q: 如何提交 Bug 或建议？

请在 GitHub 仓库提交 Issue。

## 截图预览

### 命令行界面

```
🔍 找到 2 个 XML 文件
🔍 开始解析...
  ✅ /path/to/scan1.xml
  ✅ /path/to/scan2.xml

📈 统计信息:
  文件数：2
  主机数：10 (存活：8)
  端口数：45 (开放：32)
  脚本/漏洞：5

✅ 完成！输出：report.xlsx
```

### 图形界面

```
┌────────────────────────────────────────┐
│  🔍 Nmap XML to Excel Converter        │
├────────────────────────────────────────┤
│  输入路径：[____________] [浏览...]    │
│  输出文件：[____________] [浏览...]    │
├────────────────────────────────────────┤
│  ☑ 递归查找子目录                      │
├────────────────────────────────────────┤
│      [     开始转换     ]              │
│  进度：███████████░░░░░ 65%           │
│  📝 详细日志输出...                    │
└────────────────────────────────────────┘
```

## 更新日志

### v1.0.0

- ✅ 初始版本发布
- ✅ 支持 Nmap XML 完整解析
- ✅ 4 个工作表报告
- ✅ CLI 和 GUI 双界面
- ✅ Windows EXE 打包支持
- ✅ 完整漏洞信息提取

## 许可证

MIT License

## 作者

test233

## 致谢

- [Nmap](https://nmap.org/) - 强大的网络扫描器
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代化 Python GUI 框架
- [XlsxWriter](https://github.com/jmcnamara/XlsxWriter) - Excel 文件生成库
