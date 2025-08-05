# Flight-Tracker
Python based flight tracker that links to sqlite database.
UI built with PyQT5

Current:
- Manipulate DB file
- New Mission Creation Form
- Save & Delete Toolbar for editing main database
- Visual feedback for selected rows & unsaved changes in database.

WIP:
- Live edit exisiting rows of DB.
  - Selecting row should fill mission form.
  - Save New Mission Button should turn to Update Mission Button
- Form for adding new mission to DB.

Known Bugs:
- Error occurs when trying to save a new mission without "Wind_knots" filled

Future Updates:
- METAR/Weather API
  - User Selects Time, Date, Location (Station?)
  - Autofill weather values in new mission form from METAR
    - Wind Speed
    - Cloud Coverage
    -  
- Calibration Tracking
  - Geometric
  - Radio
