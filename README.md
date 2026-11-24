# 动态物流网络 · PySide6

一个有向网络建设与货物运输游戏，支持运输动画、中文/英文界面、存档和完整事件记录。

## 启动（Windows，Python 3.10+）

在项目目录运行：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

环境准备好后可双击 `start_demo.cmd`。没有 `py` 时，用本机 Python 的完整路径替换它。

如果出现 `No Python at ...`，说明虚拟环境引用的解释器已被删除或升级。使用可用的 Python 修复，再安装依赖：

```powershell
py -m venv --upgrade .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动脚本会检查解释器及依赖，失败时显示修复提示。建议使用独立安装的 Python 创建环境。

## 操作

- 点击起点，再点击终点建立有向边；右键取消选择。重复连接增加平行带宽，边不可删除。
- 三角形开始，方形暂停；支持 1/2/4 倍速。
- 新游戏、保存、读取、导出和中英文切换位于“设置”菜单。
- “重新排版”整理节点及连线；新节点生成时避让已有节点。
- 滚轮缩放，中键拖动，双击适应全图。
- 节点下方显示各类等待货物数量和过载倒计时。

## 规则

- 边额度为 `N + floor(N / 3)`，N 是当前节点数。5 个节点有 6 个槽位，6 个有 8 个，9 个有 12 个。
- 每 25 tick 新增节点；每 tick 生成 `1 + tick // 60` 件货物。
- 每条边每 tick 运送一件货物，每件货物每 tick 最多移动一跳。
- 按最少跳路径运输，等长路径按节点 ID 字典序选择；队列可跳过暂时无法运输的货物。路由不根据拥堵分流。
- 任一节点队列超过 12 件并持续 12 tick，游戏结束。
- 读取旧存档时采用当前边额度公式，已有边保留。

## 数据与存档

| 文件 | 内容 |
|---|---|
| `data/research.sqlite` | 会话、事件、每 tick 队列/路由/边使用率及周期快照 |
| `data/autosave.json` | 每 20 tick 自动保存 |
| `data/last_session.json` | 正常退出保存的游戏 |
| `data/preferences.json` | 语言偏好 |

保存包含完整模拟状态和随机数状态。读取后暂停并建立新研究会话；旧记录保留在数据库中。“导出本局 CSV”的 `data_json` 列保存结构化事件详情。

模拟先完成一个 tick，再播放动画。存档保存完整模拟边界，不保存未完成的视觉插值。源码运行时数据位于项目目录；打包运行时位于程序旁的 `data/`，因此程序目录需要可写。当前没有独立的历史浏览或视频回放界面。

## 验证

安装游戏依赖后运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_core.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_ui.py -v
```

界面测试在离屏模式运行，所有测试数据写入临时目录。覆盖边额度、平行带宽、路由更新、存档续玩、事件记录、布局避让、建边提示、中英文切换、暂停及动画绘制。

本仓库发布游戏本体；训练模型、研究记录和本地存档不随源码上传。
