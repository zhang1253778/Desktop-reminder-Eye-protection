# Windows Desktop Reminder (Python + Tkinter)

一个简单的 Windows 桌面提醒程序：每隔一段时间弹出一个窗口，窗口不会自动关闭，必须手动点击 `×` 关闭。

## 特性

- 默认每 25 分钟提醒一次
- 弹窗在主屏幕随机位置显示，且保持可见（`topmost`）
- 到下一个周期时，如果旧窗口还没关，不会叠加新窗口，只会把现有窗口置顶
- 支持生效时段（例如 `9-12/13-18/19-21`），仅在指定时段触发自动提醒
- “设置”窗口修改后会持久化到 `desktop_reminder_settings.json`，下次启动继续生效
- 若提醒弹窗在出现后 2 秒内被关闭，会二次确认：`真的不缓缓眼睛吗`
- 二次确认文案可在“设置”中修改，并持久化保存
- 无第三方依赖（使用 Python 内置 `tkinter`）

## 项目结构

按“提醒业务模块”组织，并在模块内分层：

```text
desktop_reminder.py                # 入口适配层（保持原启动方式）
reminder/
  application/
    runner.py                      # 启动编排、参数解析、单实例入口
  domain/
    config.py                      # 业务配置模型、参数与时段规则
  presentation/
    desktop_ui.py                  # Tk 控制窗口/提醒窗口/设置窗口
  infrastructure/
    windows_runtime.py             # Windows 托盘、互斥锁、窗口唤醒
tests/
  config_test.py                   # 对应 domain/config.py 的测试
```

分层依赖约束：

- `presentation -> domain/infrastructure`（仅做界面与交互）
- `application -> presentation/domain/infrastructure`（统一编排）
- `domain` 不依赖其他层
- `infrastructure` 不依赖 `presentation/application`

命名规范：

- Python 模块/目录统一使用小写下划线（如 `windows_runtime.py`）
- 测试文件使用 `_test.py` 后缀，并与被测模块对应（如 `tests/config_test.py` 对应 `reminder/domain/config.py`）
- 目录层级控制在 4 层以内，避免过深嵌套

## 环境要求

- Windows 10/11
- Python 3.10+
- Python 自带 `tkinter` 可用

## 运行方式

在项目目录执行：

```powershell
python .\desktop_reminder.py
```

双击后台启动（推荐）：

```text
start_desktop_reminder.bat
```

该脚本会：

- 启动提醒程序，默认显示控制窗口；可通过 `--hide-control-window` 启动后隐藏到托盘
- 在 `logs\` 目录创建日志文件（按时间戳命名）：`desktop_reminder_*.log`
- 在项目目录写入运行 PID：`desktop_reminder.pid`
- 防止重复启动：若已有实例运行，会直接唤醒现有控制窗口
- 优先使用 `pythonw`（无控制台窗口），找不到时回退 `python` / `pyw -3` / `py -3`
- 可右键托盘图标选择“退出程序”关闭

默认行为：

- 启动后先等待 25 分钟再提醒一次
- 提醒文字：`该休息一下了`
- 默认生效时段：`9-12/13-18`
- 弹窗大小：`320x140`
- 窗口标题：`提醒`
- 直接运行 `python .\desktop_reminder.py` 时控制窗口默认显示
- 通过 `start_desktop_reminder.bat` 启动时，控制窗口默认显示；传 `--hide-control-window` 时隐藏到托盘
- 托盘图标可在 `^` 隐藏图标区域找到，左键显示控制窗口，右键可退出
- 点击控制窗口右上角 `X` 时，会让用户选择“退出程序”或“隐藏到托盘”
- 勾选“本次运行记住我的选择”后，仅在当前运行周期内生效；重启程序后会再次询问
- 控制窗口提供“设置”按钮，可统一配置提醒间隔、提醒文案、快速关闭确认文案、生效时段
- 设置中提供时段预设按钮：`工作日时段`（9-12/13-18）、`全天`、`自定义`
- 设置保存后会同步写入 `desktop_reminder_settings.json`，重启程序后仍保持该配置

## 参数说明

```text
--interval-minutes   提醒间隔（分钟），默认 25
--message            提醒文本，默认 该休息一下了
--quick-close-confirm-text  提醒弹窗快速关闭时的二次确认文案，默认 真的不缓缓眼睛吗
--show-on-start      启动后立即弹一次（可选）
--window-width       弹窗宽度（像素），默认 320
--window-height      弹窗高度（像素），默认 140
--title              窗口标题，默认 提醒
--log-file           日志文件路径（可选）
--pid-file           PID 文件路径（可选）
--tray-icon          托盘图标 .ico 路径（可选，默认读取 tray_icon.ico）
--active-hours       生效时段（如 9-12/13-18/19-21，默认 9-12/13-18）
--log-retention-days 日志保留天数（默认 14，0 表示不按天清理）
--log-max-files      日志最多保留文件数（默认 100，0 表示不按数量清理）
--hide-control-window 启动时隐藏控制窗口，仅保留托盘图标（可选）
--show-control-window 保留兼容参数：显式要求显示控制窗口（可选）
```

说明：

- 若项目目录存在 `tray_icon.ico`，程序会优先使用它作为托盘图标
- 有 `tray_icon.ico` 时，任务栏窗口图标与托盘图标统一使用该文件
- 没有 `tray_icon.ico` 时，冻结为 EXE 后会优先使用 EXE 内嵌图标
- 日志会在启动时自动轮转（按天数和文件数清理）

示例：

```powershell
python .\desktop_reminder.py --interval-minutes 30 --message "站起来活动2分钟"
```

指定生效时段：

```powershell
python .\desktop_reminder.py --active-hours "9-12/13-18/19-21"
```

调试（每 0.5 分钟弹一次）：

```powershell
python .\desktop_reminder.py --interval-minutes 0.5 --show-on-start
```

也可通过 `.bat` 传参：

```powershell
.\start_desktop_reminder.bat --interval-minutes 0.5 --show-on-start
```

如果需要启动后隐藏到托盘：

```powershell
.\start_desktop_reminder.bat --hide-control-window
```

如果你想显式指定显示控制窗口（兼容参数）：

```powershell
.\start_desktop_reminder.bat --show-control-window
```

## 打包 EXE

推荐使用 PyInstaller（默认 `--onedir --windowed`，单进程更稳定）：

```powershell
.\build_exe.bat
```

该脚本会输出：

- `dist_YYYYMMDD_HHMMSS\DesktopReminder\DesktopReminder.exe`（默认 onedir）
- `dist_YYYYMMDD_HHMMSS\DesktopReminder.exe`（使用 `--onefile`）

说明：

- 如果项目根目录存在 `tray_icon.ico`，打包脚本会自动作为 EXE 图标并内嵌资源
- 若无 `tray_icon.ico`，程序会优先使用 EXE 内嵌图标（若可用）
- 如需单文件可执行包，可执行：`.\build_exe.bat --onefile`
- 如需生成“启动后隐藏到托盘”的 EXE，可追加：`--hide-control-window`
- 不加 `--hide-control-window` 时，生成 EXE 启动后默认显示控制窗口
- `--onefile` 模式在任务管理器中出现两个同名进程是 PyInstaller 引导机制的正常现象

示例：

```powershell
.\build_exe.bat --onefile --hide-control-window
```

## 开机自启（任务计划程序）

1. 打开“任务计划程序”。
2. 选择“创建任务”。
3. 常规：
   - 名称填写：`DesktopReminder`
   - 勾选“仅当用户登录时运行”（弹窗类程序推荐）
4. 触发器：
   - 新建触发器，选择“登录时”
5. 操作：
   - 新建操作，程序/脚本填写 `cmd.exe`
   - 添加参数填写：`/c "E:\my_codex\start_desktop_reminder.bat"`
   - 起始于填写：`E:\my_codex`
6. 保存并测试任务。

如果你的环境无法直接运行脚本，可在任务计划程序里改成 Python 绝对路径来执行 `desktop_reminder.py`。

## 常见问题

- 看不到弹窗：
  - 确认程序在运行（查看 `logs\desktop_reminder_*.log`）
  - 先用 `--show-on-start` 验证立即弹窗
  - 检查是否被安全软件拦截
- 弹窗位置不在副屏：
  - 当前版本默认只在主屏随机显示
- 程序关闭了：
  - 在任务栏右下角 `^` 区域找到程序图标，右键选择“退出程序”
