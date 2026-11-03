"""Chinese source strings and their English UI translations."""
EN = {
    '动态物流网络  /  DEMO': 'Dynamic Logistics Network / DEMO',
    '重新排版': 'Rearrange',
    '整理节点与连线，并适应全图': 'Rearrange nodes and edges, then fit the map',
    '设置': 'Settings', '语言': 'Language',
    '新游戏': 'New game', '保存': 'Save', '读取': 'Load', '导出本局 CSV': 'Export session CSV',
    '1× 速度': '1× speed', '2× 速度': '2× speed', '4× 速度': '4× speed',
    '开始游戏': 'Start game', '暂停游戏': 'Pause game',
    '结束': 'Game over', '暂停': 'Paused', '运行': 'Running',
    '圆形': 'Circle', '三角': 'Triangle', '方形': 'Square', '星形': 'Star', '菱形': 'Diamond',
    '无等待货物': 'No cargo waiting',
    '分数 {score}    Tick {tick}    边 {used}/{capacity}    {status}':
        'Score {score}    Tick {tick}    Edges {used}/{capacity}    {status}',
    '#{id}  等待 {count}': '#{id}  Waiting {count}',
    '过载 {remaining} tick': 'Overload {remaining} ticks',
    '缩放 {zoom:.0%}  · 滚轮缩放 / 中键拖动 / 双击适应全图':
        'Zoom {zoom:.0%}  · Wheel: zoom / Middle drag: pan / Double-click: fit map',
    '点击起点，再点击终点建边。每条边永久占用一个容量；右键取消。先建边，再开始。':
        'Click a source, then a target to build. Each edge uses one permanent slot. Right-click to cancel. Build before starting.',
    '已选起点 #{id}，点击另一节点建造永久有向边；右键取消':
        'Source #{id} selected. Click another node to build a permanent directed edge; right-click to cancel.',
    '已建造 #{source} → #{target}；再次连接可增加带宽':
        'Built #{source} → #{target}. Connect again to increase bandwidth.',
    '无法建造：边容量已满或游戏已结束': 'Cannot build: edge capacity reached or game over.',
    '运行概况\n\n节点：{nodes}\n已生成货物：{cargo}\n已交付：{delivered}\n等待：{waiting}\n平均交付延迟：{delay:.1f} tick\n随机种子：{seed}\n\n':
        'Overview\n\nNodes: {nodes}\nCargo generated: {cargo}\nDelivered: {delivered}\nWaiting: {waiting}\nMean delivery delay: {delay:.1f} ticks\nRandom seed: {seed}\n\n',
    '节点 #{id} · {shape}\n': 'Node #{id} · {shape}\n',
    '规则\n每边每 tick 运送 1 件\n平行边增加带宽\n每 25 tick 新增节点\n边容量 = 当前节点数\n＋每新增 3 节点奖励 1 边\n队列 >12 连续 12 tick 失败\n\n节点下方图形表示货物目标\n数字表示该类等待数量\n\n每 20 tick 自动存档\n所有事件记录到 SQLite':
        'Rules\n1 cargo per edge per tick\nParallel edges add bandwidth\nA new node every 25 ticks\nEdge capacity = node count\n+1 per 3 additional nodes\nQueue >12 for 12 ticks: game over\n\nSymbols below nodes show cargo targets; numbers show waiting counts.\n\nAutosave every 20 ticks\nAll events recorded in SQLite',
    '游戏结束：节点持续过载。可保存、导出数据或新建游戏。':
        'Game over: sustained node overload. You can save, export data or start a new game.',
    '已重新排版节点与连线。滚轮缩放，中键拖动画面，双击适应全图。':
        'Layout updated. Wheel to zoom, middle-drag to pan, double-click to fit the map.',
    '开始新游戏？当前记录保留在数据库中，未保存的进度将离开。':
        'Start a new game? Records stay in the database; unsaved progress will be left behind.',
    '保存游戏': 'Save game', '导出事件数据': 'Export event data', '读取游戏': 'Load game',
    '保存失败': 'Save failed', '读取失败': 'Load failed',
    '已保存当前完整模拟边界；动画状态无需保存。':
        'Saved the complete simulation state. Animation progress does not need to be saved.',
    '读取成功。已创建独立研究会话，点击开始继续。':
        'Loaded into a separate research session. Press Start to continue.',
    '本局事件已导出 CSV；data_json 列保存完整结构化数据。':
        'Session exported to CSV. The data_json column contains full structured data.',
}


def translate(language, source, **values):
    return (EN.get(source, source) if language == 'en' else source).format(**values)
