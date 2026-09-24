"""Desktop workers, lazy image loading, and intentional interactive hover."""
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QTimer, Signal, Qt, QUrl
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkRequest
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QComboBox, QPushButton, QApplication


class TaskSignals(QObject):
    done = Signal(int, object, str)
    progress = Signal(str)


class Task(QRunnable):
    def __init__(self, number, function):
        super().__init__()
        self.number, self.function = number, function
        self.signals = TaskSignals()

    def run(self):
        try:
            self.signals.done.emit(self.number, self.function(self.signals.progress.emit), "")
        except Exception as error:
            self.signals.done.emit(self.number, None, str(error))


class ImageLoader(QObject):
    loaded = Signal(str, QPixmap)
    failed = Signal(str)

    def __init__(self, cache_path: Path, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager(self)
        cache = QNetworkDiskCache(self)
        cache.setCacheDirectory(str(cache_path))
        cache.setMaximumCacheSize(100*1024*1024)
        self.manager.setCache(cache)
        self.memory: dict[str, QPixmap] = {}
        self.pending = set()

    def request(self, url: str | None):
        if not url:
            return
        if url in self.memory:
            pixmap = self.memory[url]
            QTimer.singleShot(0, lambda: self.loaded.emit(url, pixmap))
            return
        if url in self.pending:
            return
        self.pending.add(url)
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(15000)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.PreferCache)
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.ManualRedirectPolicy)
        reply = self.manager.get(request)
        reply.readyRead.connect(lambda: reply.abort() if reply.bytesAvailable() > 4*1024*1024 else None)
        def finished():
            self.pending.discard(url)
            pixmap = QPixmap()
            if reply.error() == reply.NetworkError.NoError and pixmap.loadFromData(reply.readAll()):
                if len(self.memory) >= 160:
                    self.memory.pop(next(iter(self.memory)))
                self.memory[url] = pixmap
                self.loaded.emit(url, pixmap)
            else:
                self.failed.emit(url)
            reply.deleteLater()
        reply.finished.connect(finished)


class AnalyticsPopup(QFrame):
    entered = Signal()
    left = Signal()
    timeframe = Signal(object)
    archetype = Signal(str)

    def __init__(self):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumWidth(360)
        self.setMaximumWidth(430)
        self.setStyleSheet("QFrame { background:#f7f8fb; color:#1c2434; border:1px solid #bcc6d6; } QLabel {border:0;} QPushButton {padding:6px;text-align:left;}")
        layout = QVBoxLayout(self)
        self.title = QLabel()
        self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.period = QComboBox()
        for label, days in (("Last 7 days", 7), ("Last 30 days", 30), ("Last 60 days", 60), ("Last 90 days", 90), ("Current Format", None)):
            self.period.addItem(label, days)
        self.period.setCurrentIndex(1)
        self.period.currentIndexChanged.connect(lambda: self.timeframe.emit(self.period.currentData()))
        layout.addWidget(self.period)
        self.stats = QLabel()
        self.stats.setWordWrap(True)
        self.stats.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.stats)
        self.rows = QVBoxLayout()
        layout.addLayout(self.rows)
        self.context = QLabel()
        self.context.setWordWrap(True)
        self.context.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.context)

    def enterEvent(self, event):
        self.entered.emit()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.left.emit()
        super().leaveEvent(event)

    def render(self, name: str, result: dict):
        self.title.setText(name)
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        sample = result["sample_size"]
        if not sample:
            self.stats.setText("No usable cached decklists in this timeframe. Refresh competitive data or choose a wider period.")
        else:
            copies = result["average_copies"]
            self.stats.setText(f"Standard usage: {result['usage_percent']:.1f}%\nAverage copies when included: {copies if copies is not None else '—'}\nSample: {sample} fully mapped lists • {result['events']} events\nIncluded in {result['included_decks']} lists\nTop archetypes (% of lists including this card):")
        for row in result["top_archetypes"]:
            button = QPushButton(f"{row['name']}   {row['share_percent']:.1f}% ({row['decks']})")
            button.clicked.connect(lambda checked=False, key=row["id"]: self.archetype.emit(key))
            self.rows.addWidget(button)
        observed = f"{str(result['observed_from'])[:10]} to {str(result['observed_to'])[:10]}" if sample else "No cached coverage"
        self.context.setText(f"Play! Limitless cached sample\n{observed}\nExcluded unresolved lists: {result['excluded_unresolved']}\nNot all tournaments; no win-rate inference.")
        self.adjustSize()


class HoverController(QObject):
    """One shared popup; 2000ms dwell and a 220ms card-to-popup crossing grace."""
    requested = Signal(str)

    def __init__(self, popup: AnalyticsPopup, parent=None):
        super().__init__(parent)
        self.popup, self.card_id, self.anchor = popup, None, None
        self.dwell = QTimer(self)
        self.dwell.setSingleShot(True)
        self.dwell.setInterval(2000)
        self.dwell.timeout.connect(lambda: self.requested.emit(self.card_id) if self.card_id else None)
        self.grace = QTimer(self)
        self.grace.setSingleShot(True)
        self.grace.setInterval(220)
        self.grace.timeout.connect(self.cancel)
        popup.entered.connect(self.grace.stop)
        popup.left.connect(self.grace.start)

    def enter(self, card_id, widget):
        self.grace.stop()
        if card_id == self.card_id and self.popup.isVisible():
            return
        self.popup.hide()
        self.card_id, self.anchor = card_id, widget
        self.dwell.start()

    def leave(self):
        self.dwell.stop()
        self.grace.start()

    def show(self):
        if not self.card_id or self.grace.isActive():
            return
        point = QCursor.pos()
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        x = min(point.x()+18, bounds.right()-self.popup.width())
        y = min(point.y()+8, bounds.bottom()-self.popup.height())
        self.popup.move(max(bounds.left(), x), max(bounds.top(), y))
        self.popup.show()

    def cancel(self):
        self.dwell.stop()
        self.grace.stop()
        self.popup.hide()
        self.card_id = None
