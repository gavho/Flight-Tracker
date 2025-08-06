import sys
from PyQt5.QtWidgets import (
    QMainWindow, QMessageBox, QTableWidgetItem, QApplication, QToolBar, QAction, QScrollArea, QLineEdit,
    QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QWidget
)
from PyQt5.QtGui import QIcon, QColor, QBrush, QFont
from PyQt5.QtCore import Qt
from PyQt5.uic import loadUi
from db.database import Session
from db.models import Mission
from datetime import datetime, date


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Load the UI file created in Qt Designer
        loadUi("ui/flight_log.ui", self)

        # Resize the window to a larger size
        self.resize(1200, 800)

        # --- Database Session ---
        self.session = Session()

        # --- State Flags ---
        self.updating_table = False
        self.is_undoing = False
        self.is_redoing = False
        self.form_is_visible = True

        # --- Edit Tracking ---
        self.edited_cells = {}
        self.undo_stack = []
        self.redo_stack = []
        self.current_edit_original_value = None
        self.current_selected_mission_id = None

        # New set to track unsaved rows by their temporary ID
        self.unsaved_rows = {}

        # --- Connect Original UI Element Signals ---
        self.saveNewMissionButton.clicked.connect(self.save_new_mission)
        self.updateMissionButton.clicked.connect(self.update_mission)
        self.missionTable.cellPressed.connect(self.cell_pressed_for_edit)
        self.missionTable.cellChanged.connect(self.cell_was_edited)
        self.missionTable.cellClicked.connect(self.load_mission_to_form)

        # --- Setup Toolbar and Form UI ---
        self.create_toolbar()
        self.setup_form_ui()
        self.load_missions()

    def setup_form_ui(self):
        """Sets up the layout and widgets within the mission input form."""
        # Change the date input format to hide the time
        self.dateInput.setCalendarPopup(True)
        self.dateInput.setDisplayFormat("yyyy-MM-dd")

        # Get the scroll area's content widget and its existing layout.
        content_widget = self.scrollArea.widget()
        if content_widget:
            form_layout = content_widget.layout()
            if form_layout and isinstance(form_layout, QGridLayout):
                # We need to restructure the layout to add the title at the top
                # Create a new top-level layout
                main_layout = QVBoxLayout()

                # Add a title label for the form at the top
                title_label = QLabel("Mission Editor")
                title_font = QFont("Arial", 16, QFont.Bold)
                title_label.setFont(title_font)
                title_label.setAlignment(Qt.AlignCenter)
                main_layout.addWidget(title_label)

                # Add the existing QGridLayout below the title
                main_layout.addLayout(form_layout)

                # Set the new layout for the content widget
                content_widget.setLayout(main_layout)

                # Add labels with asterisks for required fields
                required_fields = {
                    'labelPlatform': 'Platform',
                    'labelChassis': 'Chassis',
                    'labelCustomer': 'Customer',
                    'labelSite': 'Site',
                    'labelAltitude': 'Altitude',
                    'labelSpeed': 'Speed',
                    'labelSpacing': 'Spacing',
                    'labelSky': 'Sky',
                    'labelWind': 'Wind',
                    'labelBattery': 'Battery',
                    'labelIsTest': 'Test?',
                    'labelOutcome': 'Outcome'
                }

                # Update the text for each of the required labels
                for label_name, text in required_fields.items():
                    label = getattr(self, label_name, None)
                    if label:
                        label.setText(f'<span style="color:red">*</span> {text}')
                        label.setTextFormat(Qt.RichText)

                # Create a layout for the buttons and add it to the last row of the grid layout
                button_layout = QHBoxLayout()
                button_layout.addStretch(1)
                button_layout.addWidget(self.saveNewMissionButton)
                button_layout.addWidget(self.updateMissionButton)
                button_layout.addStretch(1)
                form_layout.addLayout(button_layout, form_layout.rowCount(), 0, 1, form_layout.columnCount())

        # The form is initially visible
        self.scrollArea.setVisible(self.form_is_visible)
        self.updateMissionButton.hide()
        self.saveNewMissionButton.show()

    def create_toolbar(self):
        """Creates and configures the main toolbar with actions."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # --- Refresh Action ---
        self.refresh_action = QAction(QIcon.fromTheme("view-refresh"), "Refresh", self)
        self.refresh_action.setStatusTip("Reload all missions from the database")
        self.refresh_action.triggered.connect(self.load_missions)
        toolbar.addAction(self.refresh_action)

        # --- Save Edits Action ---
        self.save_action = QAction(QIcon.fromTheme("document-save"), "Save Edits", self)
        self.save_action.setStatusTip("Save all pending changes to the database")
        self.save_action.triggered.connect(self.save_edits)
        toolbar.addAction(self.save_action)

        # --- Delete Row Action ---
        self.delete_action = QAction(QIcon.fromTheme("edit-delete"), "Delete Selected Row", self)
        self.delete_action.setStatusTip("Delete the currently selected mission")
        self.delete_action.triggered.connect(self.delete_selected)
        toolbar.addAction(self.delete_action)

        # --- Create New Row Action ---
        self.create_row_action = QAction(QIcon.fromTheme("list-add"), "Create New Row", self)
        self.create_row_action.setStatusTip("Creates a new empty row in the table")
        self.create_row_action.triggered.connect(self.create_new_empty_row)
        toolbar.addAction(self.create_row_action)

        # --- Undo Action ---
        self.undo_action = QAction(QIcon.fromTheme("edit-undo"), "Undo", self)
        self.undo_action.setStatusTip("Undo the last cell edit")
        self.undo_action.triggered.connect(self.undo_last_edit)
        toolbar.addAction(self.undo_action)

        # --- Redo Action ---
        self.redo_action = QAction(QIcon.fromTheme("edit-redo"), "Redo", self)
        self.redo_action.setStatusTip("Redo the last undone cell edit")
        self.redo_action.triggered.connect(self.redo_last_edit)
        toolbar.addAction(self.redo_action)

        # --- Toggle Form Action ---
        self.toggle_form_action = QAction(QIcon.fromTheme("pan-down"), "Toggle Form", self)
        self.toggle_form_action.setStatusTip("Show/Hide the new mission input form")
        self.toggle_form_action.triggered.connect(self.toggle_form)
        toolbar.addAction(self.toggle_form_action)

    def load_missions(self):
        """Loads all missions from the database and populates the table."""
        if self.edited_cells:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "You have unsaved changes. Do you want to discard them and reload?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        self.updating_table = True
        self.edited_cells.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.unsaved_rows.clear()
        self.updateMissionButton.hide()
        self.saveNewMissionButton.show()

        self.missionTable.setRowCount(0)
        # This header list should match the number of columns and the Mission model attributes
        headers = [
            "ID", "Associated", "Date", "Platform", "Chassis", "Customer", "Site",
            "Altitude (m)", "Speed (m/s)", "Spacing (m)", "Sky", "Wind (kts)",
            "Battery", "Filesize (GB)", "Test?", "HW Issues", "Operator Issues",
            "SW Issues", "Outcome", "Comments", "Raw METAR"
        ]
        self.missionTable.setColumnCount(len(headers))
        self.missionTable.setHorizontalHeaderLabels(headers)

        missions = self.session.query(Mission).all()
        for row_idx, m in enumerate(missions):
            self.missionTable.insertRow(row_idx)
            values = [
                m.id, m.associated_mission, m.date.strftime('%Y-%m-%d') if m.date else "",
                m.platform, m.chassis, m.customer, m.site, m.altitude_m,
                m.speed_m_s, m.spacing_m, m.sky_conditions, m.wind_knots,
                m.battery, m.filesize_gb, "Yes" if m.is_test else "No",
                m.issues_hw, m.issues_operator, m.issues_sw, m.outcome,
                m.comments, m.raw_metar
            ]

            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(str(val or ""))
                self.missionTable.setItem(row_idx, col_idx, item)

            # Set the vertical header to the row number
            self.missionTable.setVerticalHeaderItem(row_idx, QTableWidgetItem(str(row_idx + 1)))

        self.missionTable.resizeColumnsToContents()

        # Adjust column widths for "Altitude", "Speed", and "Spacing"
        # Get the width of the altitude column after it's been resized
        altitude_col_width = self.missionTable.columnWidth(7)
        self.missionTable.setColumnWidth(8, altitude_col_width)  # Speed
        self.missionTable.setColumnWidth(9, altitude_col_width)  # Spacing

        self.updating_table = False

    def cell_pressed_for_edit(self, row, col):
        """Slot for the cellPressed signal. Stores the cell's value before an edit."""
        if self.updating_table:
            return
        item = self.missionTable.item(row, col)
        if item:
            self.current_edit_original_value = item.text()

    def cell_was_edited(self, row, col):
        """
        Slot for the cellChanged signal. Tracks the edit, adds it to the undo
        stack, and applies visual feedback.
        """
        if self.updating_table or self.is_undoing or self.is_redoing:
            return

        new_value = self.missionTable.item(row, col).text()
        old_value = self.current_edit_original_value

        if new_value == old_value:
            return  # No actual change occurred

        # --- Track the Edit ---
        # Add to undo stack
        self.undo_stack.append({'row': row, 'col': col, 'old': old_value, 'new': new_value})
        self.redo_stack.clear()  # Clear redo stack on new edit
        # If this is the first time this cell is edited since the last save,
        # store its very original value.
        if (row, col) not in self.edited_cells:
            self.edited_cells[(row, col)] = old_value

        # --- Apply Visual Feedback ---
        # Highlight the edited cell
        self.missionTable.item(row, col).setBackground(QColor(255, 255, 204))  # Light yellow
        # Add an asterisk to the row header to mark it as "dirty"
        header_item = self.missionTable.verticalHeaderItem(row)
        if header_item and not header_item.text().endswith('*'):
            header_item.setText(f"{row + 1}*")

    def undo_last_edit(self):
        """Reverts the last change made by the user."""
        if not self.undo_stack:
            return  # Nothing to undo

        self.is_undoing = True

        last_action = self.undo_stack.pop()
        self.redo_stack.append(last_action)
        row, col = last_action['row'], last_action['col']
        old_value = last_action['old']

        # Revert the cell's text in the table widget
        self.missionTable.item(row, col).setText(old_value)

        # Check if the cell's value has been reverted to its original, pre-edit state
        original_value_for_cell = self.edited_cells.get((row, col))
        if original_value_for_cell is not None and old_value == original_value_for_cell:
            # If so, this cell is no longer "dirty"
            del self.edited_cells[(row, col)]
            # Remove the cell's highlight
            self.missionTable.item(row, col).setBackground(QBrush(Qt.white))

            # Check if any other cells in the same row are still dirty
            row_is_still_dirty = any(r == row for r, c in self.edited_cells.keys())
            if not row_is_still_dirty:
                # If not, remove the asterisk from the row header
                header_item = self.missionTable.verticalHeaderItem(row)
                if header_item:
                    header_item.setText(str(row + 1))

        self.is_undoing = False

    def redo_last_edit(self):
        """Reapplies the last change that was undone."""
        if not self.redo_stack:
            return  # Nothing to redo

        self.is_redoing = True

        last_undone_action = self.redo_stack.pop()
        self.undo_stack.append(last_undone_action)
        row, col = last_undone_action['row'], last_undone_action['col']
        new_value = last_undone_action['new']

        # Reapply the cell's text in the table widget
        self.missionTable.item(row, col).setText(new_value)

        # Re-apply visual feedback for the edited cell
        self.missionTable.item(row, col).setBackground(QColor(255, 255, 204))
        header_item = self.missionTable.verticalHeaderItem(row)
        if header_item and not header_item.text().endswith('*'):
            header_item.setText(f"{row + 1}*")

        self.is_redoing = False

    def save_edits(self):
        """Commits all tracked changes in the `edited_cells` dictionary to the database."""
        if not self.edited_cells and not self.unsaved_rows:
            QMessageBox.information(self, "No Changes", "There are no pending edits to save.")
            return

        # Map column index to database model attribute name and type
        column_map = {
            1: ("associated_mission", int), 2: ("date", datetime), 3: ("platform", str),
            4: ("chassis", str), 5: ("customer", str), 6: ("site", str),
            7: ("altitude_m", float), 8: ("speed_m_s", float),
            9: ("spacing_m", float), 10: ("sky_conditions", str),
            11: ("wind_knots", float), 12: ("battery", str),
            13: ("filesize_gb", float), 14: ("is_test", bool),
            15: ("issues_hw", str), 16: ("issues_operator", str),
            17: ("issues_sw", str), 18: ("outcome", str),
            19: ("comments", str), 20: ("raw_metar", str)
        }

        # Group changes by mission ID to process updates efficiently
        missions_to_update = {}

        # Group edited cells by row to handle updates
        edited_rows = {row for row, col in self.edited_cells.keys()}
        try:
            for row in edited_rows:
                mission_id_item = self.missionTable.item(row, 0)
                if not mission_id_item or not mission_id_item.text().isdigit():
                    # This case should ideally not happen for existing missions but is a safeguard
                    continue

                mission_id = int(mission_id_item.text())
                if mission_id not in missions_to_update:
                    missions_to_update[mission_id] = {}

                for col in range(self.missionTable.columnCount()):
                    if (row, col) in self.edited_cells:
                        attr, type_func = column_map.get(col, (None, None))
                        if attr:
                            item = self.missionTable.item(row, col)
                            value = item.text() if item else ""
                            try:
                                if value.strip() == "":
                                    # Allow empty strings for nullable fields
                                    processed_value = None
                                elif type_func == datetime:
                                    # Use the new format string for parsing
                                    processed_value = datetime.strptime(value, '%Y-%m-%d')
                                elif type_func == bool:
                                    processed_value = value.strip().lower() in ["yes", "true", "1"]
                                else:
                                    processed_value = type_func(value)
                                missions_to_update[mission_id][attr] = processed_value
                            except (ValueError, TypeError):
                                QMessageBox.critical(self, "Input Error",
                                                     f"Invalid value '{value}' in column '{self.missionTable.horizontalHeaderItem(col).text()}' for mission ID {mission_id}.")
                                self.session.rollback()
                                return

            new_missions_data = []
            for row, temp_id in self.unsaved_rows.items():
                new_mission_data = {}
                for col in range(1, self.missionTable.columnCount()):
                    attr, type_func = column_map.get(col, (None, None))
                    if attr:
                        item = self.missionTable.item(row, col)
                        value = item.text() if item else ""
                        try:
                            if value.strip() == "":
                                processed_value = None
                            elif type_func == datetime:
                                # Use the new format string for parsing
                                processed_value = datetime.strptime(value, '%Y-%m-%d')
                            elif type_func == bool:
                                processed_value = value.strip().lower() in ["yes", "true", "1"]
                            else:
                                processed_value = type_func(value)
                            new_mission_data[attr] = processed_value
                        except (ValueError, TypeError):
                            QMessageBox.critical(self, "Input Error",
                                                 f"Invalid value '{value}' in column '{self.missionTable.horizontalHeaderItem(col).text()}' for new mission.")
                            self.session.rollback()
                            return

                # Validate mandatory fields for new rows
                if not new_mission_data.get('platform') or not new_mission_data.get('chassis'):
                    QMessageBox.critical(self, "Input Error", "New missions require 'Platform' and 'Chassis'.")
                    self.session.rollback()
                    return
                new_missions_data.append(new_mission_data)

            # Handle updates to existing missions
            for mission_id, changes in missions_to_update.items():
                mission = self.session.query(Mission).get(mission_id)
                if mission:
                    for attr, value in changes.items():
                        setattr(mission, attr, value)

            # Handle creation of new missions
            for data in new_missions_data:
                new_mission = Mission(**data)
                self.session.add(new_mission)

            self.session.commit()
            QMessageBox.information(self, "Success",
                                    f"Successfully saved changes for {len(missions_to_update)} mission(s) and created {len(new_missions_data)} new mission(s).")
            # Clear edits and reload to reset the state
            self.edited_cells.clear()
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.unsaved_rows.clear()
            self.load_missions()

        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Save Failed", f"Could not save changes:\n{str(e)}")

    def delete_selected(self):
        """Deletes the currently selected row(s) from the table and the database."""
        selected_rows = sorted(list(set(index.row() for index in self.missionTable.selectedIndexes())))
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "No row selected for deletion.")
            return

        missions_to_delete = []
        unsaved_rows_to_delete = []
        for row in selected_rows:
            mission_id_item = self.missionTable.item(row, 0)
            if mission_id_item and mission_id_item.text().startswith("NEW_"):
                unsaved_rows_to_delete.append(row)
            else:
                try:
                    mission_id = int(mission_id_item.text())
                    mission = self.session.query(Mission).get(mission_id)
                    if mission:
                        missions_to_delete.append(mission)
                except (ValueError, AttributeError):
                    pass  # Skip invalid or missing IDs

        if not missions_to_delete and not unsaved_rows_to_delete:
            QMessageBox.information(self, "Info", "No valid missions selected for deletion.")
            return

        # Handle deletion of unsaved rows first, without a database transaction
        if unsaved_rows_to_delete:
            for row in sorted(unsaved_rows_to_delete, reverse=True):
                self.missionTable.removeRow(row)
                if row in self.unsaved_rows:
                    del self.unsaved_rows[row]
            QMessageBox.information(self, "Deletion", f"Deleted {len(unsaved_rows_to_delete)} unsaved row(s).")

        if missions_to_delete:
            reply = QMessageBox.question(self, "Confirm Deletion",
                                         f"Are you sure you want to delete {len(missions_to_delete)} selected mission(s) from the database?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    for mission in missions_to_delete:
                        self.session.delete(mission)
                    self.session.commit()
                    QMessageBox.information(self, "Success",
                                            f"Successfully deleted {len(missions_to_delete)} mission(s).")
                    self.load_missions()
                except Exception as e:
                    self.session.rollback()
                    QMessageBox.critical(self, "Delete Failed", f"Could not delete missions:\n{str(e)}")

    def create_new_empty_row(self):
        """Adds a new empty row to the table for manual data entry."""
        row_count = self.missionTable.rowCount()
        self.missionTable.insertRow(row_count)

        # Determine the next sequential ID for the new row
        max_db_id = self.session.query(Mission).order_by(Mission.id.desc()).first()
        max_db_id = max_db_id.id if max_db_id else 0

        max_unsaved_id = 0
        for temp_id in self.unsaved_rows.values():
            try:
                # Extract the number from the temporary ID (e.g., "NEW_123")
                num = int(temp_id.split('_')[1])
                if num > max_unsaved_id:
                    max_unsaved_id = num
            except (ValueError, IndexError):
                continue

        next_id = max(max_db_id, max_unsaved_id) + 1

        temp_id = f"NEW_{next_id}"
        self.unsaved_rows[row_count] = temp_id

        id_item = QTableWidgetItem(temp_id)
        id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
        self.missionTable.setItem(row_count, 0, id_item)

        self.missionTable.setVerticalHeaderItem(row_count, QTableWidgetItem(f"{row_count + 1}*"))

        # Scroll the table to the newly created row
        self.missionTable.scrollToBottom()

    def toggle_form(self):
        """Toggles the visibility of the new mission input form."""
        self.form_is_visible = not self.form_is_visible
        self.scrollArea.setVisible(self.form_is_visible)

    def load_mission_to_form(self, row, col):
        """
        Populates the new mission form with data from the selected table row
        and changes the button to "Update Mission".
        """
        if not self.form_is_visible:
            return

        mission_id_item = self.missionTable.item(row, 0)
        if not mission_id_item or mission_id_item.text().startswith("NEW_"):
            self.clear_form()
            self.current_selected_mission_id = None
            self.updateMissionButton.hide()
            self.saveNewMissionButton.show()
            return

        try:
            self.current_selected_mission_id = int(mission_id_item.text())
        except (ValueError, AttributeError):
            self.clear_form()
            self.current_selected_mission_id = None
            self.updateMissionButton.hide()
            self.saveNewMissionButton.show()
            return

        # Parse the date from the table without time
        date_str = self.missionTable.item(row, 2).text()
        if date_str:
            self.dateInput.setDate(datetime.strptime(date_str, '%Y-%m-%d'))
        else:
            self.dateInput.clear()

        self.platformInput.setText(self.missionTable.item(row, 3).text())
        self.chassisInput.setText(self.missionTable.item(row, 4).text())
        self.customerInput.setText(self.missionTable.item(row, 5).text())
        self.siteInput.setText(self.missionTable.item(row, 6).text())
        self.altitudeInput.setText(self.missionTable.item(row, 7).text())
        self.speedInput.setText(self.missionTable.item(row, 8).text())
        self.spacingInput.setText(self.missionTable.item(row, 9).text())
        self.skyInput.setCurrentText(self.missionTable.item(row, 10).text())
        self.windInput.setText(self.missionTable.item(row, 11).text())
        self.batteryInput.setText(self.missionTable.item(row, 12).text())
        self.filesizeInput.setText(self.missionTable.item(row, 13).text())
        self.isTestInput.setChecked(self.missionTable.item(row, 14).text() == "Yes")
        self.issuesHwInput.setText(self.missionTable.item(row, 15).text())
        self.issuesOperatorInput.setText(self.missionTable.item(row, 16).text())
        self.issuesSwInput.setText(self.missionTable.item(row, 17).text())
        self.outcomeInput.setText(self.missionTable.item(row, 18).text())
        self.commentsInput.setText(self.missionTable.item(row, 19).text())
        self.rawMetarInput.setPlainText(self.missionTable.item(row, 20).text())

        self.saveNewMissionButton.hide()
        self.updateMissionButton.show()

    def clear_form(self):
        """Clears all input fields in the form."""
        self.dateInput.clear()
        self.platformInput.clear()
        self.chassisInput.clear()
        self.customerInput.clear()
        self.siteInput.clear()
        self.altitudeInput.clear()
        self.speedInput.clear()
        self.spacingInput.clear()
        self.skyInput.setCurrentIndex(0)
        self.windInput.clear()
        self.batteryInput.clear()
        self.filesizeInput.clear()
        self.isTestInput.setChecked(False)
        self.issuesHwInput.clear()
        self.issuesOperatorInput.clear()
        self.issuesSwInput.clear()
        self.outcomeInput.clear()
        self.commentsInput.clear()
        self.rawMetarInput.clear()

    def update_mission(self):
        """Updates an existing mission in the database using the form fields."""
        if not self.current_selected_mission_id:
            QMessageBox.warning(self, "No Mission Selected", "Please select a mission from the table to update.")
            return

        try:
            mission = self.session.query(Mission).get(self.current_selected_mission_id)
            if not mission:
                QMessageBox.critical(self, "Error", "Selected mission not found in the database.")
                return

            # Extract only the date part and set the time to 00:00:00
            if self.dateInput.text():
                date_only = self.dateInput.date().toPyDate()
                mission.date = datetime.combine(date_only, datetime.min.time())
            else:
                mission.date = None

            mission.platform = self.get_text(self.platformInput)
            mission.chassis = self.get_text(self.chassisInput)
            mission.customer = self.get_text(self.customerInput)
            mission.site = self.get_text(self.siteInput)
            mission.altitude_m = self.get_float(self.altitudeInput, "Altitude (m)")
            mission.speed_m_s = self.get_float(self.speedInput, "Speed (m/s)")
            mission.spacing_m = self.get_float(self.spacingInput, "Spacing (m)")
            mission.sky_conditions = self.skyInput.currentText() or None
            mission.wind_knots = self.get_float(self.windInput, "Wind (kts)")
            mission.battery = self.get_text(self.batteryInput)
            mission.filesize_gb = self.get_float(self.filesizeInput, "Filesize (GB)")
            mission.is_test = self.isTestInput.isChecked()
            mission.issues_hw = self.get_text(self.issuesHwInput)
            mission.issues_operator = self.get_text(self.issuesOperatorInput)
            mission.issues_sw = self.get_text(self.issuesSwInput)
            mission.outcome = self.get_text(self.outcomeInput)
            mission.comments = self.get_text(self.commentsInput)
            mission.raw_metar = self.rawMetarInput.toPlainText().strip() or None

            self.session.commit()
            QMessageBox.information(self, "Success", "Mission updated successfully.")
            self.load_missions()

        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Could not update mission:\n{str(e)}")

    def get_text(self, widget):
        if isinstance(widget, QLineEdit):
            return widget.text().strip() or None
        return None

    def get_float(self, widget, field_name):
        text = widget.text().strip()
        try:
            return float(text) if text else None
        except ValueError:
            raise ValueError(f"Invalid value for '{field_name}': '{text}'. Please enter a number.")

    def save_new_mission(self):
        """Saves a new mission from the input form fields at the bottom."""
        try:
            # Extract only the date part and set the time to 00:00:00
            if self.dateInput.text():
                date_only = self.dateInput.date().toPyDate()
                date_value = datetime.combine(date_only, datetime.min.time())
            else:
                date_value = None

            m = Mission(
                associated_mission=None,
                date=date_value,
                platform=self.get_text(self.platformInput),
                chassis=self.get_text(self.chassisInput),
                customer=self.get_text(self.customerInput),
                site=self.get_text(self.siteInput),
                altitude_m=self.get_float(self.altitudeInput, "Altitude (m)"),
                speed_m_s=self.get_float(self.speedInput, "Speed (m/s)"),
                spacing_m=self.get_float(self.spacingInput, "Spacing (m)"),
                sky_conditions=self.skyInput.currentText() or None,
                wind_knots=self.get_float(self.windInput, "Wind (kts)"),
                battery=self.get_text(self.batteryInput),
                filesize_gb=self.get_float(self.filesizeInput, "Filesize (GB)"),
                is_test=self.isTestInput.isChecked(),
                issues_hw=self.get_text(self.issuesHwInput),
                issues_operator=self.get_text(self.issuesOperatorInput),
                issues_sw=self.get_text(self.issuesSwInput),
                outcome=self.get_text(self.outcomeInput),
                comments=self.get_text(self.commentsInput),
                raw_metar=self.rawMetarInput.toPlainText().strip() or None
            )

            self.session.add(m)
            self.session.commit()
            QMessageBox.information(self, "Success", "New mission saved successfully.")
            self.load_missions()
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", str(e))
        except Exception as e:
            self.session.rollback()
            QMessageBox.critical(self, "Error", f"Could not save new mission:\n{str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())