from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QTableWidgetItem
)
from PyQt5.uic import loadUi
from db.database import Session
from db.models import Mission
from datetime import datetime


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/flight_log.ui", self)

        self.session = Session()
        self.editing_mission_id = None
        self.unsaved_row_indices = set()

        # Toolbar actions
        self.actionRefresh.triggered.connect(self.load_missions)
        self.actionDelete.triggered.connect(self.delete_selected)

        # Buttons
        self.saveButton.clicked.connect(self.save_or_update_mission)

        # Table
        self.missionTable.itemSelectionChanged.connect(self.populate_form_from_selected)
        self.missionTable.itemChanged.connect(self.mark_row_as_unsaved)

        self.load_missions()

    def load_missions(self):
        self.missionTable.blockSignals(True)
        missions = self.session.query(Mission).all()
        self.missionTable.setRowCount(0)
        self.missionTable.setColumnCount(21)
        self.missionTable.setHorizontalHeaderLabels([
            "ID", "Associated", "Date", "Platform", "Chassis", "Customer", "Site",
            "Altitude (m)", "Speed (m/s)", "Spacing (m)", "Sky", "Wind (kts)",
            "Battery", "Filesize (GB)", "Test?", "HW Issues", "Operator Issues",
            "SW Issues", "Outcome", "Comments", "Raw METAR"
        ])

        for row_idx, m in enumerate(missions):
            self.missionTable.insertRow(row_idx)
            values = [
                m.id, m.associated_mission or "", m.date.strftime('%Y-%m-%d %H:%M') if m.date else "",
                m.platform, m.chassis, m.customer, m.site, m.altitude_m,
                m.speed_m_s, m.spacing_m, m.sky_conditions, m.wind_knots,
                m.battery, m.filesize_gb, "Yes" if m.is_test else "No",
                m.issues_hw, m.issues_operator, m.issues_sw, m.outcome,
                m.comments, m.raw_metar
            ]

            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(str(val or ""))
                self.missionTable.setItem(row_idx, col_idx, item)

        self.unsaved_row_indices.clear()
        self.missionTable.blockSignals(False)

    def get_text(self, widget):
        return widget.text().strip()

    def get_float(self, widget):
        text = widget.text().strip()
        try:
            return float(text) if text else None
        except ValueError:
            return None  # Allow optional float inputs

    def populate_form_from_selected(self):
        row = self.missionTable.currentRow()
        if row < 0:
            return

        self.editing_mission_id = int(self.missionTable.item(row, 0).text())
        mission = self.session.query(Mission).get(self.editing_mission_id)
        if not mission:
            return

        # Populate form
        self.dateInput.setDateTime(mission.date or datetime.now())
        self.platformInput.setText(mission.platform or "")
        self.chassisInput.setText(mission.chassis or "")
        self.customerInput.setText(mission.customer or "")
        self.siteInput.setText(mission.site or "")
        self.altitudeInput.setText(mission.altitude_m or "")
        self.speedInput.setText(mission.speed_m_s or "")
        self.spacingInput.setText(mission.spacing_m or "")
        self.skyInput.setCurrentText(mission.sky_conditions or "")
        self.windInput.setText(str(mission.wind_knots or ""))
        self.batteryInput.setText(mission.battery or "")
        self.filesizeInput.setText(str(mission.filesize_gb or ""))
        self.isTestInput.setChecked(mission.is_test)
        self.issuesHwInput.setText(mission.issues_hw or "")
        self.issuesOperatorInput.setText(mission.issues_operator or "")
        self.issuesSwInput.setText(mission.issues_sw or "")
        self.outcomeInput.setText(mission.outcome or "")
        self.commentsInput.setText(mission.comments or "")
        self.rawMetarInput.setPlainText(mission.raw_metar or "")

        self.saveButton.setText("Update Mission")

    def save_or_update_mission(self):
        try:
            if self.editing_mission_id:
                mission = self.session.query(Mission).get(self.editing_mission_id)
            else:
                mission = Mission()

            mission.date = self.dateInput.dateTime().toPyDateTime()
            mission.platform = self.get_text(self.platformInput)
            mission.chassis = self.get_text(self.chassisInput)
            mission.customer = self.get_text(self.customerInput)
            mission.site = self.get_text(self.siteInput)
            mission.altitude_m = self.get_text(self.altitudeInput)
            mission.speed_m_s = self.get_text(self.speedInput)
            mission.spacing_m = self.get_text(self.spacingInput)
            mission.sky_conditions = self.skyInput.currentText()
            mission.wind_knots = self.get_float(self.windInput)
            mission.battery = self.get_text(self.batteryInput)
            mission.filesize_gb = self.get_float(self.filesizeInput)
            mission.is_test = self.isTestInput.isChecked()
            mission.issues_hw = self.get_text(self.issuesHwInput)
            mission.issues_operator = self.get_text(self.issuesOperatorInput)
            mission.issues_sw = self.get_text(self.issuesSwInput)
            mission.outcome = self.get_text(self.outcomeInput)
            mission.comments = self.get_text(self.commentsInput)
            mission.raw_metar = self.rawMetarInput.toPlainText().strip()

            if not self.editing_mission_id:
                self.session.add(mission)

            self.session.commit()
            QMessageBox.information(self, "Success", "Mission saved.")
            self.editing_mission_id = None
            self.saveButton.setText("Save New Mission")
            self.load_missions()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save mission:\n{str(e)}")

    def delete_selected(self):
        row = self.missionTable.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Warning", "No row selected.")
            return

        mission_id = self.missionTable.item(row, 0).text()
        mission = self.session.query(Mission).get(int(mission_id))
        if mission:
            self.session.delete(mission)
            self.session.commit()
            self.load_missions()

    def mark_row_as_unsaved(self, item):
        row = item.row()
        self.unsaved_row_indices.add(row)
        for col in range(self.missionTable.columnCount()):
            cell = self.missionTable.item(row, col)
            if cell:
                cell.setBackground(Qt.yellow)
