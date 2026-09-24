"""Qt interaction tests; optional desktop dependency, no live network."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QTest, QSignalSpy
from pokelab.ui_support import AnalyticsPopup, HoverController, ImageLoader
from pokelab.desktop import MainWindow, QuantityControl
from test_desktop_engine import engine


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_hover_requires_two_seconds_and_cancels_early(app):
    popup, anchor = AnalyticsPopup(), QWidget()
    controller = HoverController(popup)
    spy = QSignalSpy(controller.requested)
    controller.enter("sm2-1", anchor)
    QTest.qWait(400)
    controller.leave()
    QTest.qWait(1800)
    assert spy.count() == 0
    controller.enter("sm2-1", anchor)
    QTest.qWait(1750)
    assert spy.count() == 0
    QTest.qWait(400)
    assert spy.count() == 1
    controller.leave()
    popup.entered.emit()
    QTest.qWait(300)
    assert controller.card_id == "sm2-1"
    popup.left.emit()
    QTest.qWait(300)
    assert controller.card_id is None
    popup.close()


def test_browser_scope_filter_and_variant_controls(app, engine, monkeypatch):
    monkeypatch.setattr(ImageLoader, "request", lambda *args: None)
    window = MainWindow(engine)
    window.category.setCurrentIndex(1)
    window.types["Psychic"].setChecked(True)
    window.types["Dragon"].setChecked(True)
    assert window.engine.browse(window.query())["total"] == 2
    controls = window.gallery.widget().findChildren(QuantityControl)
    control = next(c for c in controls if c.card_id == "sm2-1")
    control.variant.setCurrentText("holo")
    control.adjust(1)
    QTest.qWait(400)
    assert engine.collection_quantity("sm2-1", "holo") == 1
    control = next(c for c in window.gallery.widget().findChildren(QuantityControl) if c.card_id == "sm2-1")
    assert control.variant.currentText() == "holo"
    window.scope.setCurrentIndex(1)
    assert window.engine.browse(window.query())["total"] == 1
    window.view.setCurrentIndex(1)
    assert window.stack.currentIndex() == 1 and window.table.rowCount() == 1
    window.select_card("sm2-1")
    window.preview_context()
    assert "Psychic Card" in window.answer.toPlainText()
    window.close()
