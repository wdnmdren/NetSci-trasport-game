"""Game UI regression checks; all save data stays in a temporary directory."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
QT_AVAILABLE = importlib.util.find_spec('PySide6') is not None
if QT_AVAILABLE:
    from PySide6.QtWidgets import QApplication
    import main


@unittest.skipUnless(QT_AVAILABLE, 'Install requirements.txt to run UI tests')
class GameUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        main.configure_app(cls.app)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(main, 'DATA', Path(self.folder.name)/'data')
        self.data_patch.start()
        self.window = main.Window()
        self.window.timer.stop()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.data_patch.stop()
        self.folder.cleanup()

    def test_build_hint_accepts_source_keyword_and_language_switch(self):
        self.window.set_hint('已建造 #{source} → #{target}；再次连接可增加带宽', source=0, target=1)
        self.assertIn('#0', self.window.hint.text())
        self.assertIn('#1', self.window.hint.text())
        self.window.set_language('en')
        self.assertIn('#0', self.window.hint.text())
        self.assertIn('floor(node count / 3)', self.window.details.text())
        self.window.set_language('zh')
        self.assertIn('floor(节点数 / 3)', self.window.details.text())

    def test_pause_and_layout_preserve_game_state(self):
        self.assertTrue(self.window.paused)
        self.window.toggle()
        self.assertFalse(self.window.paused)
        self.window.toggle()
        self.assertTrue(self.window.paused)
        self.window.game.build(0, 1)
        edges = [dict(edge) for edge in self.window.game.state['edges']]
        self.window.relayout()
        self.assertEqual(self.window.game.state['edges'], edges)
        self.assertEqual(self.window.game.state['tick'], 0)

    def test_simulation_autosave_and_animation_render(self):
        self.window.game.build(0, 1)
        self.window.toggle()
        for _ in range(20):
            self.window.progress = 1
            self.window.frame()
        self.assertEqual(self.window.game.state['tick'], 20)
        self.assertTrue((main.DATA/'autosave.json').exists())
        self.window.progress = .5
        self.app.processEvents()
        screenshot = self.window.map.grab()
        self.assertFalse(screenshot.isNull())


if __name__ == '__main__':
    unittest.main()
