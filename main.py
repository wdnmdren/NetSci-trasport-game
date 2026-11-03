import math
import json
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath, QPolygonF, QFontDatabase, QFont, QIcon, QPixmap, QTransform, QActionGroup
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                              QLabel, QPushButton, QComboBox, QFileDialog, QMessageBox, QMenu)
from core import Game, Recorder, SHAPES
from i18n import translate

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
COLORS = dict(zip(SHAPES, ['#42c9be', '#f4bc65', '#79a6f6', '#e399da', '#b4a1ff']))
NAMES = dict(zip(SHAPES, ['圆形', '三角', '方形', '星形', '菱形']))


def symbol(p, shape, x, y, radius):
    p.setBrush(QColor(COLORS[shape]))
    p.setPen(QPen(QColor('#122032'), 1.5))
    if shape == 'circle':
        p.drawEllipse(QPointF(x, y), radius, radius)
        return
    if shape == 'square':
        p.drawRect(QRectF(x-radius, y-radius, radius*2, radius*2))
        return
    count = 10 if shape == 'star' else 3 if shape == 'triangle' else 4
    points = []
    for i in range(count):
        angle = -math.pi/2 + math.tau*i/count
        r = radius * (.45 if shape == 'star' and i % 2 else 1)
        points.append(QPointF(x+math.cos(angle)*r, y+math.sin(angle)*r))
    p.drawPolygon(QPolygonF(points))


class Map(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setMinimumSize(640, 500)
        self.source = None
        self.selected = None
        self.drag_position = None
        self.zoom = 1.
        self.auto_fit = True
        self.fit_view()

    def fit_view(self):
        nodes = self.window.game.state['nodes']
        left, right = min(n['x'] for n in nodes)-100, max(n['x'] for n in nodes)+100
        top, bottom = min(n['y'] for n in nodes)-95, max(n['y'] for n in nodes)+130
        self.center = QPointF((left+right)/2,(top+bottom)/2)
        self.reference_size = (max(700,right-left),max(550,bottom-top))
        self.zoom = 1.
        self.auto_fit = True
        self.update()

    def view_transform(self):
        scale = min(self.width()/self.reference_size[0],self.height()/self.reference_size[1])*self.zoom
        t = QTransform()
        t.translate(self.width()/2,self.height()/2)
        t.scale(scale,scale)
        t.translate(-self.center.x(),-self.center.y())
        return t

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if not delta:
            return
        anchor = event.position()
        before = self.view_transform().inverted()[0].map(anchor)
        self.zoom = max(.15,min(6.,self.zoom*math.exp(delta*.0015)))
        after = self.view_transform().inverted()[0].map(anchor)
        self.center += before-after
        self.auto_fit = False
        self.update()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_position is not None:
            inverse = self.view_transform().inverted()[0]
            self.center += inverse.map(self.drag_position)-inverse.map(event.position())
            self.drag_position = event.position()
            self.auto_fit = False
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.drag_position = None
            self.unsetCursor()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.source = None
            self.fit_view()

    def geometry_for(self, edge):
        edges = self.window.game.state['edges']
        nodes = self.window.game.state['nodes']
        a, b = nodes[edge['source']], nodes[edge['target']]
        peers = [e for e in edges if e['source']==a['id'] and e['target']==b['id']]
        index = next(i for i,e in enumerate(peers) if e['id']==edge['id'])
        dx, dy = b['x']-a['x'], b['y']-a['y']
        length = max(1, math.hypot(dx,dy))
        offset = 20 + index*19
        path = QPainterPath(QPointF(a['x'], a['y']))
        path.quadTo(QPointF((a['x']+b['x'])/2-dy/length*offset,
                           (a['y']+b['y'])/2+dx/length*offset), QPointF(b['x'], b['y']))
        return path

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor('#101b2c'))
        p.setTransform(self.view_transform())
        p.setPen(QPen(QColor('#1d2a3d'), 1))
        inverse = self.view_transform().inverted()[0]
        visible = inverse.mapRect(QRectF(self.rect()))
        grid = 60 if self.zoom < .5 else 30
        for x in range(math.floor(visible.left()/grid)*grid, math.ceil(visible.right()), grid):
            for y in range(math.floor(visible.top()/grid)*grid, math.ceil(visible.bottom()), grid):
                p.drawPoint(x,y)
        s = self.window.game.state
        for edge in s['edges']:
            path = self.geometry_for(edge)
            p.setPen(QPen(QColor('#536d8d'), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            tip, tail = path.pointAtPercent(.72), path.pointAtPercent(.69)
            angle = math.atan2(tip.y()-tail.y(),tip.x()-tail.x())
            p.setBrush(QColor('#91accd'))
            p.drawPolygon(QPolygonF([tip, QPointF(tip.x()-10*math.cos(angle-.45), tip.y()-10*math.sin(angle-.45)),
                                   QPointF(tip.x()-10*math.cos(angle+.45), tip.y()-10*math.sin(angle+.45))]))
        for move in self.window.moves:
            edge = s['edges'][move['edge']]
            pos = self.geometry_for(edge).pointAtPercent(self.window.progress)
            symbol(p, move['shape'], pos.x(),pos.y(),6)
        for node in s['nodes']:
            x,y = node['x'],node['y']
            p.setPen(QPen(QColor('#ff6e83' if node['overload'] else '#42617e'), 3 if node['overload'] else 1))
            p.setBrush(QColor('#17283e'))
            p.drawEllipse(QPointF(x,y),32,32)
            if node['id'] == self.source:
                p.setPen(QPen(QColor('#e8f3ff'), 2, Qt.PenStyle.DashLine))
                p.drawEllipse(QPointF(x,y),39,39)
            symbol(p,node['shape'],x,y,16)
            p.setPen(QColor('#d7e5f7'))
            p.drawText(QRectF(x-55,y+36,110,24), Qt.AlignmentFlag.AlignCenter,
                       self.window.tr_text('#{id}  等待 {count}',id=node['id'],count=len(node['queue'])))
            counts = [(shape, sum(s['cargo'][cid]['target'] == shape for cid in node['queue']))
                      for shape in SHAPES]
            counts = [(shape, count) for shape, count in counts if count]
            if counts:
                # Two compact rows keep even five cargo types readable beside a node.
                for row in range((len(counts)+2)//3):
                    items = counts[row*3:row*3+3]
                    start = x-len(items)*44/2
                    for column, (shape, count) in enumerate(items):
                        left, top = start+column*44, y+67+row*23
                        symbol(p, shape, left+7, top, 6)
                        p.setPen(QColor('#d7e5f7'))
                        p.drawText(QRectF(left+17,top-10,28,20),Qt.AlignmentFlag.AlignVCenter,str(count))
            else:
                p.setPen(QColor('#7890aa'))
                p.drawText(QRectF(x-65,y+61,130,20),Qt.AlignmentFlag.AlignCenter,self.window.tr_text('无等待货物'))
            if node['overload']:
                p.setPen(QColor('#ff8393'))
                p.drawText(QRectF(x-55,y-60,110,22),Qt.AlignmentFlag.AlignCenter,
                           self.window.tr_text('过载 {remaining} tick',remaining=s['overload_duration']-node['overload']))
        p.resetTransform()
        p.setPen(QColor('#7890aa'))
        p.drawText(12,self.height()-12,self.window.tr_text('缩放 {zoom:.0%}  · 滚轮缩放 / 中键拖动 / 双击适应全图',zoom=self.zoom))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        point = self.view_transform().inverted()[0].map(event.position())
        x,y = point.x(),point.y()
        node = next((n for n in self.window.game.state['nodes'] if math.hypot(n['x']-x,n['y']-y)<36),None)
        if event.button() == Qt.MouseButton.RightButton or node is None:
            self.source = None
        elif self.source is None:
            self.source = node['id']
            self.selected = node['id']
            self.window.set_hint('已选起点 #{id}，点击另一节点建造永久有向边；右键取消',id=self.source)
        elif self.source != node['id']:
            a,b = self.source,node['id']
            self.source = None
            self.window.finish_tick()
            if self.window.game.build(a,b):
                self.window.recorder.flush(self.window.game)
                self.window.set_hint('已建造 #{source} → #{target}；再次连接可增加带宽',source=a,target=b)
            else:
                self.window.set_hint('无法建造：边容量已满或游戏已结束')
        self.window.refresh()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        DATA.mkdir(exist_ok=True)
        try:
            self.language = json.loads((DATA/'preferences.json').read_text(encoding='utf-8')).get('language','zh')
        except (OSError, ValueError, AttributeError):
            self.language = 'zh'
        if self.language not in ('zh','en'):
            self.language = 'zh'
        self.game = Game()
        self.recorder = Recorder(DATA/'research.sqlite', self.game)
        self.moves = []
        self.progress = 1.
        self.paused = True
        self.speed = 1
        self.setWindowTitle('Dynamic Logistics Network · PySide6 Demo')
        self.resize(1220,800)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        header = QHBoxLayout()
        title = QLabel('动态物流网络  /  DEMO')
        self.title_label = title
        title.setStyleSheet('font-size:20px;font-weight:700;color:#62d6c9')
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)
        toolbar = QHBoxLayout()
        self.status = QLabel()
        self.status.setStyleSheet('background:#17263b;border-radius:6px;padding:12px;font-size:15px;')
        toolbar.addWidget(self.status, 1)
        self.pause_button = QPushButton()
        self.pause_button.setFixedSize(42,42)
        self.pause_button.clicked.connect(self.toggle)
        toolbar.addWidget(self.pause_button)
        self.layout_button = QPushButton('重新排版')
        self.layout_button.setToolTip('整理节点与连线，并适应全图')
        self.layout_button.clicked.connect(self.relayout)
        toolbar.addWidget(self.layout_button)
        speed = QComboBox()
        self.speed_combo = speed
        speed.setMinimumWidth(115)
        speed.addItems(['1× 速度','2× 速度','4× 速度'])
        speed.currentIndexChanged.connect(lambda i: setattr(self,'speed',2**i))
        speed.currentIndexChanged.connect(self.record_speed)
        toolbar.addWidget(speed)
        self.settings_button = QPushButton('设置')
        self.settings_menu = QMenu(self)
        self.menu_actions = []
        for text, action in [('新游戏',self.new),('保存',self.save),('读取',self.load),('导出本局 CSV',self.export)]:
            self.menu_actions.append((text,self.settings_menu.addAction(text,action)))
        self.settings_menu.addSeparator()
        self.language_menu = self.settings_menu.addMenu('语言')
        self.language_group = QActionGroup(self)
        self.language_actions = {}
        for code,label in [('zh','中文'),('en','English')]:
            action = self.language_menu.addAction(label)
            action.setCheckable(True)
            self.language_group.addAction(action)
            action.triggered.connect(lambda checked,code=code: self.set_language(code))
            self.language_actions[code] = action
        self.settings_button.setMenu(self.settings_menu)
        toolbar.addWidget(self.settings_button)
        layout.addLayout(toolbar)
        body = QHBoxLayout()
        self.map = Map(self)
        body.addWidget(self.map, 1)
        self.details = QLabel()
        self.details.setFixedWidth(245)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details.setWordWrap(True)
        self.details.setStyleSheet('background:#17263b;padding:18px;line-height:1.5')
        body.addWidget(self.details)
        layout.addLayout(body,1)
        self.hint = QLabel('点击起点，再点击终点建边。每条边永久占用一个容量；右键取消。先建边，再开始。')
        self.hint.setWordWrap(True)
        self.hint_source = '点击起点，再点击终点建边。每条边永久占用一个容量；右键取消。先建边，再开始。'
        self.hint_values = {}
        layout.addWidget(self.hint)
        self.timer = QTimer(self)
        self.elapsed = QElapsedTimer()
        self.elapsed.start()
        self.timer.timeout.connect(self.frame)
        self.timer.start(16)
        self.apply_language()

    def tr_text(self, source, **values):
        return translate(self.language,source,**values)

    def set_hint(self, source, **values):
        self.hint_source, self.hint_values = source, values
        self.hint.setText(self.tr_text(source,**values))

    def set_language(self, language):
        self.language = language
        temporary = DATA/'preferences.tmp'
        temporary.write_text(json.dumps({'language':language}),encoding='utf-8')
        temporary.replace(DATA/'preferences.json')
        self.apply_language()

    def apply_language(self):
        self.title_label.setText(self.tr_text('动态物流网络  /  DEMO'))
        self.layout_button.setText(self.tr_text('重新排版'))
        self.layout_button.setToolTip(self.tr_text('整理节点与连线，并适应全图'))
        self.settings_button.setText(self.tr_text('设置'))
        self.language_menu.setTitle(self.tr_text('语言'))
        for source,action in self.menu_actions:
            action.setText(self.tr_text(source))
        for code,action in self.language_actions.items():
            action.setChecked(code==self.language)
        for index,source in enumerate(['1× 速度','2× 速度','4× 速度']):
            self.speed_combo.setItemText(index,self.tr_text(source))
        self.set_hint(self.hint_source,**self.hint_values)
        self.refresh()

    def refresh(self):
        s = self.game.state
        self.status.setText(self.tr_text('分数 {score}    Tick {tick}    边 {used}/{capacity}    {status}',
                            score=s['score'],tick=s['tick'],used=len(s['edges']),capacity=self.game.capacity,
                            status=self.tr_text('结束' if s['ended'] else '暂停' if self.paused else '运行')))
        icon = QPixmap(24,24)
        icon.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#62d6c9'))
        if self.paused:
            painter.drawPolygon(QPolygonF([QPointF(7,4),QPointF(21,12),QPointF(7,20)]))
        else:
            painter.drawRoundedRect(QRectF(5,5,14,14),1,1)
        painter.end()
        self.pause_button.setIcon(QIcon(icon))
        self.pause_button.setToolTip(self.tr_text('开始游戏' if self.paused else '暂停游戏'))
        self.pause_button.setAccessibleName(self.tr_text('开始游戏' if self.paused else '暂停游戏'))
        delivered = [c for c in s['cargo'].values() if c['delivered'] is not None]
        delay = sum(c['delivered']-c['created'] for c in delivered)/max(1,len(delivered))
        text = self.tr_text('运行概况\n\n节点：{nodes}\n已生成货物：{cargo}\n已交付：{delivered}\n等待：{waiting}\n平均交付延迟：{delay:.1f} tick\n随机种子：{seed}\n\n',
                            nodes=len(s['nodes']),cargo=len(s['cargo']),delivered=len(delivered),
                            waiting=sum(len(n['queue']) for n in s['nodes']),delay=delay,seed=s['seed'])
        if self.map.selected is not None and self.map.selected < len(s['nodes']):
            n = s['nodes'][self.map.selected]
            text += self.tr_text('节点 #{id} · {shape}\n',id=n['id'],shape=self.tr_text(NAMES[n['shape']]))
            for shape in SHAPES:
                count = sum(s['cargo'][c]['target']==shape for c in n['queue'])
                if count:
                    text += f"  {self.tr_text(NAMES[shape])}: {count}\n"
            text += '\n'
        text += self.tr_text('规则\n每边每 tick 运送 1 件\n平行边增加带宽\n每 25 tick 新增节点\n边容量 = 当前节点数\n＋每新增 3 节点奖励 1 边\n队列 >12 连续 12 tick 失败\n\n节点下方图形表示货物目标\n数字表示该类等待数量\n\n每 20 tick 自动存档\n所有事件记录到 SQLite')
        self.details.setText(text)
        self.map.update()

    def frame(self):
        delta = min(self.elapsed.restart()/1000, .1)
        if self.paused:
            return
        if self.progress < 1:
            self.progress = min(1.,self.progress+delta*self.speed)
            self.map.update()
            return
        self.finish_tick()
        if self.game.state['ended']:
            self.paused = True
            self.set_hint('游戏结束：节点持续过载。可保存、导出数据或新建游戏。')
            self.refresh()
            return
        old_node_count = len(self.game.state['nodes'])
        self.moves = self.game.step()
        if len(self.game.state['nodes']) != old_node_count and self.map.auto_fit:
            self.map.fit_view()
        self.progress = 0.
        self.recorder.flush(self.game)
        if self.game.state['tick'] % 20 == 0:
            self.game.save(DATA/'autosave.json')
        self.refresh()

    def finish_tick(self):
        self.progress = 1.
        self.moves = []

    def toggle(self):
        self.paused = not self.paused
        self.game.event('pause_changed', paused=self.paused)
        self.recorder.flush(self.game)
        self.refresh()

    def record_speed(self, index):
        self.game.event('speed_changed', speed=2**index)
        self.recorder.flush(self.game)

    def relayout(self):
        self.game.relayout()
        self.recorder.flush(self.game)
        self.map.fit_view()
        self.set_hint('已重新排版节点与连线。滚轮缩放，中键拖动画面，双击适应全图。')
        self.refresh()

    def new(self):
        dialog = QMessageBox(QMessageBox.Icon.Question,self.tr_text('新游戏'),
                             self.tr_text('开始新游戏？当前记录保留在数据库中，未保存的进度将离开。'),
                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,self)
        dialog.button(QMessageBox.StandardButton.Yes).setText('Yes' if self.language=='en' else '是')
        dialog.button(QMessageBox.StandardButton.No).setText('No' if self.language=='en' else '否')
        if dialog.exec() != QMessageBox.StandardButton.Yes:
            return
        self.recorder.db.close()
        self.game = Game()
        self.recorder = Recorder(DATA/'research.sqlite',self.game)
        self.paused = True
        self.finish_tick()
        self.map.source = self.map.selected = None
        self.map.fit_view()
        self.refresh()

    def save(self):
        path,_ = self.choose_file('保存游戏',DATA/'save.json','JSON (*.json)',save=True)
        if path:
            try:
                self.game.save(path)
                self.set_hint('已保存当前完整模拟边界；动画状态无需保存。')
            except Exception as e:
                QMessageBox.warning(self,self.tr_text('保存失败'),str(e))

    def load(self):
        path,_ = self.choose_file('读取游戏',DATA,'JSON (*.json)',save=False)
        if path:
            try:
                game = Game.load(path)
                self.recorder.db.close()
                self.game = game
                self.recorder = Recorder(DATA/'research.sqlite',game)
                self.paused = True
                self.finish_tick()
                self.map.source = self.map.selected = None
                self.map.fit_view()
                self.refresh()
                self.set_hint('读取成功。已创建独立研究会话，点击开始继续。')
            except Exception as e:
                QMessageBox.warning(self,self.tr_text('读取失败'),str(e))

    def export(self):
        path,_ = self.choose_file('导出事件数据',DATA/'events.csv','CSV (*.csv)',save=True)
        if path:
            self.recorder.export(path)
            self.set_hint('本局事件已导出 CSV；data_json 列保存完整结构化数据。')

    def choose_file(self, title, path, file_filter, save):
        # Native file dialogs follow the OS language; use Qt's own dialog here.
        dialog = QFileDialog(self,self.tr_text(title),str(path),file_filter)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
        labels = [(QFileDialog.DialogLabel.LookIn,'Look in:','位置：'),
                  (QFileDialog.DialogLabel.FileName,'File name:','文件名：'),
                  (QFileDialog.DialogLabel.FileType,'Files of type:','文件类型：'),
                  (QFileDialog.DialogLabel.Accept,('Save' if save else 'Open'),('保存' if save else '打开')),
                  (QFileDialog.DialogLabel.Reject,'Cancel','取消')]
        for label,en,zh in labels:
            dialog.setLabelText(label,en if self.language=='en' else zh)
        if save:
            dialog.setDefaultSuffix('csv' if 'CSV' in file_filter else 'json')
        if dialog.exec():
            return dialog.selectedFiles()[0],dialog.selectedNameFilter()
        return '', ''

    def closeEvent(self,event):
        self.game.save(DATA/'last_session.json')
        self.recorder.flush(self.game)
        self.recorder.db.close()
        event.accept()


def configure_app(app):
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
    app.setFont(QFont('Microsoft YaHei', 10))
    app.setStyle('Fusion')
    app.setStyleSheet('QWidget {background:#101b2c;color:#dce8f7;font-family:"Microsoft YaHei";font-size:13px;} QPushButton,QComboBox {background:#243952;border:1px solid #38536e;border-radius:6px;padding:9px;} QPushButton:hover {background:#34526e;} QLabel {border:none;}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    configure_app(app)
    window = Window()
    window.show()
    sys.exit(app.exec())
