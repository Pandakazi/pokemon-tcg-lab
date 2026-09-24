"""Windows desktop shell. All data operations call native engine functions."""
import argparse
from contextlib import closing
from datetime import date
import json
from pathlib import Path
import sys
import threading

from PySide6.QtCore import Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QScrollArea, QSplitter, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QStackedWidget, QTextEdit, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QDateEdit)

from tcg_lab.sync_cards import synchronize
from .engine import PokeLabEngine, CardQuery, POKEMON_TYPES
from .analytics import Analytics, LimitlessClient
from .agent import SelectedCardAgent, PROVIDERS
from .images import TCGdexImages
from .paths import prepare_data
from .secrets import SecretStore
from .ui_support import Task, ImageLoader, AnalyticsPopup, HoverController
from .presentation import card_text, deck_text


class QuantityControl(QWidget):
    changed = Signal()

    def __init__(self, engine, card_id, choices=None, parent=None):
        super().__init__(parent)
        self.engine, self.card_id = engine, card_id
        self.choices = choices if choices is not None else {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.variant = QComboBox()
        self.variant.addItems(engine.variants(card_id))
        self.variant.setCurrentText(self.choices.get(card_id, "unspecified"))
        self.variant.setToolTip("Physical finish variant; unspecified is kept separately.")
        self.variant.currentIndexChanged.connect(self.load)
        self.quantity = QSpinBox()
        self.quantity.setRange(0, 9999)
        self.quantity.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.quantity.setFixedWidth(55)
        self.quantity.editingFinished.connect(self.save)
        minus, plus = QPushButton("−"), QPushButton("+")
        for button in (minus, plus):
            button.setFixedWidth(28)
        minus.clicked.connect(lambda: self.adjust(-1))
        plus.clicked.connect(lambda: self.adjust(1))
        for widget in (self.variant, minus, self.quantity, plus):
            layout.addWidget(widget)
        self.load()

    def load(self):
        self.choices[self.card_id] = self.variant.currentText()
        self.quantity.setValue(self.engine.collection_quantity(self.card_id, self.variant.currentText()))

    def adjust(self, amount):
        self.quantity.setValue(self.quantity.value()+amount)
        self.save()

    def save(self):
        self.engine.set_quantity(self.card_id, self.variant.currentText(), self.quantity.value())
        self.changed.emit()


class CardTile(QFrame):
    selected = Signal(str)

    def __init__(self, card, engine, loader, images, hover, on_quantity, choices):
        super().__init__()
        self.card, self.hover = card, hover
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(255)
        layout = QVBoxLayout(self)
        self.image = QLabel("Loading card image…")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setFixedSize(225, 285)
        self.image.setWordWrap(True)
        self.image.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.image)
        name = QLabel(card["name"])
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setWordWrap(True)
        layout.addWidget(name)
        meta = QLabel(f"{card.get('set',{}).get('name','')} • {card.get('localId','')}\n{card['id']} • Owned total: {card['owned']}")
        meta.setTextFormat(Qt.TextFormat.PlainText)
        meta.setWordWrap(True)
        layout.addWidget(meta)
        control = QuantityControl(engine, card["id"], choices)
        control.changed.connect(on_quantity)
        layout.addWidget(control)
        self.image_url = images.url(card)
        if not self.image_url:
            self.image.setText("No image available from TCGdex")
        loader.loaded.connect(self.image_ready)
        loader.failed.connect(self.image_failed)
        loader.request(self.image_url)

    @Slot(str)
    def image_failed(self, url):
        if url == self.image_url:
            self.image.setText("Image unavailable — card text is still available")

    @Slot(str, QPixmap)
    def image_ready(self, url, pixmap):
        if url == self.image_url:
            self.image.setPixmap(pixmap.scaled(self.image.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def enterEvent(self, event):
        self.hover.enter(self.card["id"], self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover.leave()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.card["id"])
        super().mousePressEvent(event)


class CardTable(QTableWidget):
    entered_card = Signal(str)
    left_card = Signal()

    def __init__(self):
        super().__init__(0, 6)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setHorizontalHeaderLabels(["Card", "Set / number", "Type", "Owned", "Printing", "Quantity by variant"])
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.card_ids = []
        self.last_row = -1
        self.cellEntered.connect(self.enter_row)

    def enter_row(self, row, column):
        if row != self.last_row and row < len(self.card_ids):
            self.last_row = row
            self.entered_card.emit(self.card_ids[row])

    def leaveEvent(self, event):
        self.last_row = -1
        self.left_card.emit()
        super().leaveEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, engine, secrets, parent):
        super().__init__(parent)
        self.setWindowTitle("PokéLab Settings")
        self.engine, self.secrets = engine, secrets
        layout = QFormLayout(self)
        self.provider = QComboBox()
        self.provider.addItems(PROVIDERS)
        self.model = QLineEdit(engine.setting("model") or "claude-haiku-4-5-20251001")
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Leave blank to keep the saved API key")
        self.start = QLineEdit(engine.setting("format_start") or "")
        self.start.setPlaceholderText("YYYY-MM-DD; defines Current Format timeframe")
        for label, widget in (("Provider", self.provider), ("Model", self.model), ("API key", self.key), ("Current Format starts", self.start)):
            layout.addRow(label, widget)
        notice = QLabel("The key is encrypted for your Windows account. Agent requests send only the selected card, compact statistics, and your question. Clicking Ask contacts the provider and may incur API charges.")
        notice.setWordWrap(True)
        layout.addRow(notice)
        delete = QPushButton("Delete saved API key")
        delete.clicked.connect(lambda: secrets.delete())
        layout.addRow(delete)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def save(self):
        try:
            if self.start.text().strip():
                parsed = date.fromisoformat(self.start.text().strip())
                if parsed > date.today():
                    raise ValueError("Current Format start cannot be in the future.")
            if not self.model.text().strip():
                raise ValueError("Enter the model identifier.")
            if self.key.text().strip():
                self.secrets.save(self.key.text())
            self.engine.setting("model", self.model.text().strip())
            self.engine.setting("provider", self.provider.currentText())
            self.engine.setting("format_start", self.start.text().strip())
            self.key.clear()
            self.accept()
        except (ValueError, RuntimeError) as error:
            QMessageBox.warning(self, "Settings not saved", str(error))


class MainWindow(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine, self.analytics = engine, Analytics(engine)
        self.agent = SelectedCardAgent(engine, self.analytics)
        self.secrets = SecretStore(engine.path.parent)
        self.images = TCGdexImages()
        self.loader = ImageLoader(engine.path.parent / "image-cache", self)
        self.popup = AnalyticsPopup()
        self.hover = HoverController(self.popup, self)
        self.hover.requested.connect(self.show_analytics)
        self.popup.timeframe.connect(lambda days: self.show_analytics(self.hover.card_id))
        self.popup.archetype.connect(self.open_archetype)
        self.jobs, self.task_number, self.analytics_generation = {}, 0, 0
        self.variant_choices = {}
        self.cancel_event = threading.Event()
        self.selected_id, self.page = None, 1
        self.setWindowTitle("PokéLab — Standard research & collection")
        self.resize(1400, 900)
        self.setStyleSheet("QMainWindow,QWidget {font-size:13px;} QMainWindow {background:#f5f6fa;} QPushButton {padding:6px;} QLineEdit {padding:7px;} QFrame[frameShape='6'] {background:white;} QSplitter::handle {background:#dce1e8;}")
        central = QWidget()
        outer = QVBoxLayout(central)
        self.setCentralWidget(central)
        heading = QLabel("PokéLab")
        heading.setStyleSheet("font-size:26px;font-weight:600")
        outer.addWidget(heading)
        self.coverage_label = QLabel()
        self.coverage_label.setWordWrap(True)
        outer.addWidget(self.coverage_label)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search the English Standard pool by card name or printing ID")
        self.search.returnPressed.connect(self.reset_page)
        toolbar.addWidget(self.search, 1)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.reset_page)
        toolbar.addWidget(search_button)
        self.view = QComboBox()
        self.view.addItems(["Gallery", "List"])
        self.view.currentIndexChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        toolbar.addWidget(self.view)
        for label, callback in (("Filters", self.toggle_filters), ("Refresh cards", self.refresh_cards), ("Refresh Limitless", self.refresh_limitless), ("Settings", self.settings)):
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        cancel = QPushButton("Cancel refresh")
        cancel.clicked.connect(self.cancel_event.set)
        toolbar.addWidget(cancel)
        outer.addLayout(toolbar)
        splitter = QSplitter()
        outer.addWidget(splitter, 1)
        self.filters = QWidget()
        self.filters.setMaximumWidth(220)
        rail = QVBoxLayout(self.filters)
        rail.addWidget(QLabel("Collection"))
        self.scope = QComboBox()
        for label, value in (("All", "all"), ("Owned", "owned"), ("Unowned", "unowned")):
            self.scope.addItem(label, value)
        self.scope.currentIndexChanged.connect(self.reset_page)
        rail.addWidget(self.scope)
        rail.addWidget(QLabel("Card category"))
        self.category = QComboBox()
        for label, value in (("All categories", None), ("Pokémon", "Pokemon"), ("Trainers", "Trainer"), ("Energy", "Energy")):
            self.category.addItem(label, value)
        self.category.currentIndexChanged.connect(self.reset_page)
        rail.addWidget(self.category)
        rail.addWidget(QLabel("Pokémon types (any selected)"))
        self.types = {}
        for name in POKEMON_TYPES:
            checkbox = QCheckBox(name)
            checkbox.toggled.connect(self.reset_page)
            self.types[name] = checkbox
            rail.addWidget(checkbox)
        clear = QPushButton("Clear filters")
        clear.clicked.connect(self.clear_filters)
        rail.addWidget(clear)
        rail.addStretch()
        splitter.addWidget(self.filters)
        browser = QWidget()
        browser_layout = QVBoxLayout(browser)
        self.stack = QStackedWidget()
        self.gallery = QScrollArea()
        self.gallery.setWidgetResizable(True)
        self.stack.addWidget(self.gallery)
        self.table = CardTable()
        self.table.entered_card.connect(lambda card_id: self.hover.enter(card_id, self.table))
        self.table.left_card.connect(self.hover.leave)
        self.table.cellClicked.connect(lambda row, col: self.select_card(self.table.card_ids[row]))
        self.stack.addWidget(self.table)
        browser_layout.addWidget(self.stack, 1)
        paging = QHBoxLayout()
        self.previous = QPushButton("Previous")
        self.previous.clicked.connect(lambda: self.change_page(-1))
        self.next = QPushButton("Next")
        self.next.clicked.connect(lambda: self.change_page(1))
        self.page_label = QLabel()
        for widget in (self.previous, self.page_label, self.next):
            paging.addWidget(widget)
        browser_layout.addLayout(paging)
        splitter.addWidget(browser)
        panel = QWidget()
        panel.setMinimumWidth(310)
        panel.setMaximumWidth(440)
        side = QVBoxLayout(panel)
        self.selected_label = QLabel("Select a card to inspect it or ask the Agent")
        self.selected_label.setWordWrap(True)
        self.selected_label.setTextFormat(Qt.TextFormat.PlainText)
        side.addWidget(self.selected_label)
        self.card_text = QTextEdit()
        self.card_text.setReadOnly(True)
        side.addWidget(self.card_text, 1)
        large = QPushButton("View larger card image")
        large.clicked.connect(self.large_image)
        side.addWidget(large)
        agent_button = QPushButton("Agent — read-only")
        agent_button.clicked.connect(lambda: self.agent_panel.setVisible(not self.agent_panel.isVisible()))
        side.addWidget(agent_button)
        self.agent_panel = QWidget()
        agent_layout = QVBoxLayout(self.agent_panel)
        self.agent_period = QComboBox()
        for days in (7, 30, 60, 90):
            self.agent_period.addItem(f"Last {days} days", days)
        self.agent_period.addItem("Current Format", None)
        self.agent_period.setCurrentIndex(1)
        agent_layout.addWidget(self.agent_period)
        self.question = QLineEdit()
        self.question.setMaxLength(2000)
        self.question.setPlaceholderText("What are people pairing with this?")
        agent_layout.addWidget(self.question)
        preview = QPushButton("Preview exact evidence sent to AI")
        preview.clicked.connect(self.preview_context)
        agent_layout.addWidget(preview)
        self.ask_button = QPushButton("Ask provider")
        self.ask_button.clicked.connect(self.ask_agent)
        agent_layout.addWidget(self.ask_button)
        self.answer = QTextEdit()
        self.answer.setReadOnly(True)
        agent_layout.addWidget(self.answer)
        side.addWidget(self.agent_panel, 1)
        splitter.addWidget(panel)
        splitter.setSizes([190, 840, 370])
        self.reload_timer = QTimer(self)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.setInterval(300)
        self.reload_timer.timeout.connect(self.load_cards)
        self.load_cards()

    def task(self, function, callback):
        self.task_number += 1
        number = self.task_number
        task = Task(number, function)
        self.jobs[number] = (task, callback)
        task.signals.done.connect(self.task_done)
        task.signals.progress.connect(self.statusBar().showMessage)
        QThreadPool.globalInstance().start(task)

    @Slot(int, object, str)
    def task_done(self, number, result, error):
        job = self.jobs.pop(number, None)
        if not job:
            return
        if error:
            self.ask_button.setEnabled(True)
            self.statusBar().showMessage(error)
            QMessageBox.warning(self, "Action could not finish", error)
        else:
            job[1](result)

    def query(self):
        return CardQuery(self.search.text(), self.category.currentData(), self.scope.currentData(),
                         tuple(name for name, box in self.types.items() if box.isChecked()), page=self.page)

    def reset_page(self, *args):
        self.page = 1
        self.load_cards()

    def change_page(self, amount):
        self.page = max(1, self.page+amount)
        self.load_cards()

    def clear_filters(self):
        for control in [self.scope, self.category, *self.types.values()]:
            control.blockSignals(True)
        self.scope.setCurrentIndex(0)
        self.category.setCurrentIndex(0)
        for box in self.types.values():
            box.setChecked(False)
        for control in [self.scope, self.category, *self.types.values()]:
            control.blockSignals(False)
        self.search.clear()
        self.reset_page()

    def toggle_filters(self):
        self.filters.setVisible(not self.filters.isVisible())

    def load_cards(self):
        self.hover.cancel()
        result = self.engine.browse(self.query())
        if not result["cards"] and self.page > 1:
            self.page = 1
            result = self.engine.browse(self.query())
        host = QWidget()
        grid = QGridLayout(host)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for index, card in enumerate(result["cards"]):
            tile = CardTile(card, self.engine, self.loader, self.images, self.hover, self.reload_timer.start, self.variant_choices)
            tile.selected.connect(self.select_card)
            columns = max(1, min(4, (self.width()-650)//270))
            grid.addWidget(tile, index//columns, index%columns)
        old = self.gallery.takeWidget()
        if old:
            old.deleteLater()
        self.gallery.setWidget(host)
        self.table.setRowCount(len(result["cards"]))
        self.table.card_ids = [card["id"] for card in result["cards"]]
        self.table.last_row = -1
        for row, card in enumerate(result["cards"]):
            values = [card["name"], f"{card.get('set',{}).get('name','')} {card.get('localId','')}", ", ".join(card.get("types", [])), str(card["owned"]), card["id"]]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            control = QuantityControl(self.engine, card["id"], self.variant_choices)
            control.changed.connect(self.reload_timer.start)
            self.table.setCellWidget(row, 5, control)
        self.table.resizeRowsToContents()
        self.page_label.setText(f"{result['total']} printings • Page {self.page} of {max(1,(result['total']+39)//40)}")
        self.previous.setEnabled(self.page > 1)
        self.next.setEnabled(self.page*40 < result["total"])
        coverage = self.engine.coverage()
        sync = coverage.get("last_sync") or {}
        complete = sync.get("status") == "complete"
        self.coverage_label.setText(f"English Standard • {coverage['standard_printings']} provider-legal printings • " + (f"Complete catalog synced {str(sync.get('finished_at',''))[:10]}" if complete else "Card sync incomplete — use Refresh cards before trusting pool coverage") + " • TCGdex flags are dated source evidence.")

    def select_card(self, card_id):
        self.selected_id = card_id
        record = self.engine.cards.get(card_id)
        card = record["card"]
        self.selected_label.setText(f"{card['name']} • {card_id}")
        self.card_text.setPlainText(card_text(card))
        self.answer.clear()

    def large_image(self):
        if not self.selected_id:
            return
        card = self.engine.cards.get(self.selected_id, True)["card"]
        dialog = QDialog(self)
        dialog.setWindowTitle(card["name"])
        layout = QVBoxLayout(dialog)
        label = QLabel("Loading image (requires internet unless cached)…")
        label.setMinimumSize(460, 650)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        url = self.images.url(card, True)
        def loaded(key, pixmap):
            if key == url:
                label.setPixmap(pixmap.scaled(460, 650, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.loader.loaded.connect(loaded)
        self.loader.request(url)
        dialog.exec()
        self.loader.loaded.disconnect(loaded)

    def show_analytics(self, card_id):
        if not card_id:
            return
        self.analytics_generation += 1
        generation = self.analytics_generation
        days = self.popup.period.currentData()
        def work(progress):
            return self.analytics.stats(self.engine.identity(card_id), days)
        def done(result):
            if generation == self.analytics_generation and card_id == self.hover.card_id:
                self.popup.render(self.engine.cards.get(card_id)["card"]["name"], result)
                self.hover.show()
        self.task(work, done)

    def open_archetype(self, archetype_id):
        if not self.hover.card_id:
            return
        rows = self.analytics.drilldown(self.engine.identity(self.hover.card_id), archetype_id, self.popup.period.currentData())
        self.hover.cancel()
        dialog = QDialog(self)
        dialog.setWindowTitle("Underlying Limitless decklists — up to 200 results")
        dialog.resize(950, 650)
        layout = QHBoxLayout(dialog)
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(["Event", "Player", "Place", "Date"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        detail = QTextEdit()
        detail.setReadOnly(True)
        for index, row in enumerate(rows):
            for column, value in enumerate((row["event"], row["player"], row["placing"], row["date"][:10])):
                table.setItem(index, column, QTableWidgetItem(str(value)))
        def select(row, column):
            entry = rows[row]
            detail.setPlainText(f"{entry['archetype_name']}\n{entry['source']}\n\n" + deck_text(entry["cards"]))
        table.cellClicked.connect(select)
        layout.addWidget(table, 1)
        layout.addWidget(detail, 1)
        if rows:
            select(0, 0)
        dialog.exec()

    def refresh_cards(self):
        if self.jobs:
            self.statusBar().showMessage("Wait for the current operation to finish.")
            return
        self.statusBar().showMessage("Refreshing the full TCGdex catalog…")
        self.cancel_event.clear()
        def work(progress):
            def report_progress(message):
                if self.cancel_event.is_set():
                    state = self.engine.cards.metadata("last_sync") or {}
                    state["status"] = "interrupted"
                    self.engine.cards.metadata("last_sync", state)
                    raise InterruptedError("Card refresh canceled. Downloaded records are preserved.")
                progress(message)
            report = synchronize(self.engine.cards, refresh=True, progress=report_progress)
            self.engine.rebuild_identities()
            self.analytics.remap_cached()
            return report
        def done(report):
            self.load_cards()
            self.statusBar().showMessage(f"Card refresh: {report['status']}; {report['missing']} missing, {report['failed']} failures")
        self.task(work, done)

    def refresh_limitless(self):
        if self.jobs:
            self.statusBar().showMessage("Wait for the current operation to finish.")
            return
        self.statusBar().showMessage("Refreshing up to 25 recent Standard events (90-day window, paced to respect rate limits)…")
        self.cancel_event.clear()
        self.task(lambda progress: LimitlessClient(cancel_event=self.cancel_event).refresh(self.analytics, progress=progress),
                  lambda result: self.statusBar().showMessage(f"Cached {result['imported']} events; skipped {result['skipped']}. Statistics use only the cached sample."))

    def settings(self):
        SettingsDialog(self.engine, self.secrets, self).exec()

    def preview_context(self):
        if not self.selected_id:
            self.answer.setPlainText("Select a card first.")
            return
        try:
            context = self.agent.context(self.selected_id, self.agent_period.currentData())
            self.answer.setPlainText(json.dumps(context, indent=2, ensure_ascii=False))
        except ValueError as error:
            self.answer.setPlainText(str(error))

    def ask_agent(self):
        if not self.selected_id:
            self.answer.setPlainText("Select a card first.")
            return
        try:
            key = self.secrets.load()
            if not key:
                self.answer.setPlainText("Add your API key in Settings first. The key stays encrypted on this PC.")
                return
            provider_name = self.engine.setting("provider") or "Anthropic"
            provider = PROVIDERS[provider_name](key, self.engine.setting("model") or "claude-haiku-4-5-20251001")
            card_id, question, days = self.selected_id, self.question.text(), self.agent_period.currentData()
            self.ask_button.setEnabled(False)
            self.answer.setPlainText("Reading the compact evidence…")
            def done(answer):
                self.ask_button.setEnabled(True)
                if self.selected_id == card_id:
                    self.answer.setPlainText(answer)
            self.task(lambda progress: self.agent.ask(provider, card_id, question, days), done)
        except (RuntimeError, ValueError) as error:
            self.answer.setPlainText(str(error))

    def closeEvent(self, event):
        if self.jobs:
            QMessageBox.information(self, "Operation in progress", "Please wait for the current refresh or provider request to finish before closing.")
            event.ignore()
            return
        self.popup.close()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(description="PokéLab standalone desktop")
    parser.add_argument("--data-dir", help="Optional separate profile for development/QA")
    parser.add_argument("--smoke-test", help="Render UI screenshot then exit (QA only)")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("PokéLab")
    app.setOrganizationName("PokeLab")
    app.setStyle("Fusion")
    engine = PokeLabEngine(prepare_data(args.data_dir))
    with closing(engine.cards.connect()) as db:
        missing = db.execute("SELECT count(*) FROM cards c LEFT JOIN printing_identity p ON p.printing_id=c.id WHERE p.printing_id IS NULL").fetchone()[0]
    if missing:
        engine.rebuild_identities()
    window = MainWindow(engine)
    window.show()
    if args.smoke_test:
        def capture():
            window.grab().save(args.smoke_test)
            app.quit()
        QTimer.singleShot(6000, capture)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
