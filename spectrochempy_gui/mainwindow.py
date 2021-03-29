# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

import sys
import logging
import time

from functools import partial
from setuptools_scm import get_version

import spectrochempy as scp

import spectrochempy_gui.pyqtgraph as pg
from spectrochempy_gui.pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from spectrochempy_gui.projecttree import ProjectTreeWidget
from spectrochempy_gui.plots import PlotWidget
from spectrochempy_gui.controller import Controller
from spectrochempy_gui.preferences import Preferences, GeneralPreferencesWidget
from spectrochempy_gui.utils import geticon
from spectrochempy_gui.lockeddock import LockedDock, LockedDockArea
from spectrochempy_gui.model import Project
# from spectrochempy_gui.widgets.progresswidget import QProgressIndicator

scp.core.FileDialog = QtGui.QFileDialog

# TODO: set this to False for production
__DEV__ = True


# ======================================================================================================================
class MainWindow(QtGui.QMainWindow):

    preference_pages = []

    # ..................................................................................................................
    def __init__(self, show=True):

        super().__init__()

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        siz = QtWidgets.QDesktopWidget().screenGeometry(-1)
        self.ww, self.wh = ww, wh = min(1500, siz.width() * .80), min(900, siz.height() * .80)
        self.move(QtCore.QPoint(10, 10))  # TODO: center it ?

        # --------------------------------------------------------------------------------------------------------------
        # Logging
        # --------------------------------------------------------------------------------------------------------------

        if not __DEV__:
            # production
            scp.app.log_level = logging.WARNING
        else:
            # development
            scp.app.log_level = logging.DEBUG

        # --------------------------------------------------------------------------------------------------------------
        # Main area
        # --------------------------------------------------------------------------------------------------------------

        self.area = area = LockedDockArea()
        self.setCentralWidget(area)
        self.setWindowIcon(QtGui.QIcon(str(geticon('scpy.png'))))
        self.setWindowTitle('SpectroChemPy GUI')

        # --------------------------------------------------------------------------------------------------------------
        # Create status bar
        # --------------------------------------------------------------------------------------------------------------

        self.statusbar = self.statusBar()
        self.statusbar.showMessage('Welcome to SpectroChemPy')

        # --------------------------------------------------------------------------------------------------------------
        # Create doc for plots
        # --------------------------------------------------------------------------------------------------------------

        # we need to create a dock object for this branch
        self.dplot = dplot = LockedDock('Plot', closable=False)
        dplot.hideTitleBar()

        # --------------------------------------------------------------------------------------------------------------
        # Create project window
        # --------------------------------------------------------------------------------------------------------------

        self.dproject = dproject = LockedDock("Project", size=(300, wh * .30))
        self.projectwidget = ProjectTreeWidget(showHeader=False, parent=self)

        self.project = Project(parent=self)

        dproject.addWidget(self.projectwidget)
        dproject.setMinimumWidth(300)
        dproject.setMaximumWidth(300)

        # --------------------------------------------------------------------------------------------------------------
        # Controller window
        # --------------------------------------------------------------------------------------------------------------

        dcontroller = LockedDock("Controller", size=(300, wh * .70))
        self.controller = Controller(parent=self)
        dcontroller.addWidget(self.controller)

        # --------------------------------------------------------------------------------------------------------------
        # set layout
        # --------------------------------------------------------------------------------------------------------------

        self.area.addDock(dproject, 'left')
        self.area.addDock(dplot, 'right')
        self.area.addDock(dcontroller, 'bottom', dproject)
        self.resize(ww, wh)

        # --------------------------------------------------------------------------------------------------------------
        # Create Menubar and actions
        # --------------------------------------------------------------------------------------------------------------

        # MENU FILE
        # -------------------------------------------------------------------

        project_menu = QtGui.QMenu('&Project', parent=self)
        self.menuBar().addMenu(project_menu)

        # Project menu
        # ----------------------------------------------------------------------------------------------------------

        self.new_action = QtGui.QAction('&New project', self)
        self.new_action.setShortcut(QtGui.QKeySequence.New)
        self.new_action.setStatusTip('Create a new main project')
        self.new_action.triggered.connect(partial(self.project.openProject, new=True))
        project_menu.addAction(self.new_action)

        self.open_action = QtGui.QAction('&Open project', self)
        self.open_action.setShortcut(QtGui.QKeySequence.Open)
        self.open_action.setStatusTip('Open a new main project')
        self.open_action.triggered.connect(partial(self.project.openProject, new=False))
        project_menu.addAction(self.open_action)

        # Dataset menu
        # --------------------------------------------------------------------------------------------------------------

        project_menu.addSeparator()

        self.add_dataset_action = QtGui.QAction('Add dataset', self)
        self.add_dataset_action.triggered.connect(self.project.addDataset)
        self.add_dataset_action.setShortcut(QtGui.QKeySequence('Ctrl+A', QtGui.QKeySequence.NativeText))
        self.add_dataset_action.setDisabled(True)
        project_menu.addAction(self.add_dataset_action)

        self.remove_dataset_action = QtGui.QAction('remove selected dataset', self)
        self.remove_dataset_action.triggered.connect(self.project.removeDataset)
        self.remove_dataset_action.setShortcut(QtGui.QKeySequence('Ctrl+D', QtGui.QKeySequence.NativeText))
        self.remove_dataset_action.setDisabled(True)
        project_menu.addAction(self.remove_dataset_action)

        # Save project menu
        # ----------------------------------------------------------------------------------------------------------

        project_menu.addSeparator()

        self.save_action = QtGui.QAction('&Save project', self)
        self.save_action.setStatusTip('Save the entire project into a file')
        self.save_action.setShortcut(QtGui.QKeySequence.Save)
        self.save_action.triggered.connect(partial(self.project.saveProject, force=True))
        self.save_action.setDisabled(True)
        project_menu.addAction(self.save_action)

        self.save_as_action = QtGui.QAction('Save project as...', self)
        self.save_as_action.setStatusTip('Save the entire project into a new file')
        self.save_as_action.setShortcut(QtGui.QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(partial(self.project.saveProject, force=True, saveas=True))
        self.save_as_action.setDisabled(True)
        project_menu.addAction(self.save_as_action)

        # Close project menu
        # ----------------------------------------------------------------------------------------------------------

        project_menu.addSeparator()

        self.close_action = QtGui.QAction('Close project', self)
        self.close_action.setShortcut(QtGui.QKeySequence('Ctrl+Shift+W', QtGui.QKeySequence.NativeText))
        self.close_action.setStatusTip('Close the main project and delete all data and plots out of '
                                          'memory')
        self.close_action.triggered.connect(self.project.closeProject)
        self.close_action.setDisabled(True)
        project_menu.addAction(self.close_action)

        # Quit
        # --------------------------------------------------------------------------------------------------------------

        if sys.platform != 'darwin':  # mac os makes this anyway
            quit_action = QtGui.QAction('Quit', self)
            quit_action.triggered.connect(QtCore.QCoreApplication.instance().quit)
            quit_action.setShortcut(QtGui.QKeySequence.Quit)
            project_menu.addAction(quit_action)

        self.menuBar().addMenu(project_menu)

        # Processing menu
        # ---------------
        proc_menu = QtGui.QMenu('Script', parent=self)
        self.menuBar().addMenu(proc_menu)

        # export script
        export_script_action = QtGui.QAction('Export script', self)
        export_script_action.triggered.connect(self.controller.exportScript)
        proc_menu.addAction(export_script_action)

        # import script
        import_script_action = QtGui.QAction('Import script', self)
        import_script_action.triggered.connect(self.controller.importScript)
        proc_menu.addAction(import_script_action)

        # Help menu
        # --------------------------------------------------------------------------------------------------------------

        help_menu = QtGui.QMenu('Help', parent=self)
        self.menuBar().addMenu(help_menu)

        # About

        about_action = QtGui.QAction('About', self)
        about_action.triggered.connect(self.onAbout)
        help_menu.addAction(about_action)

        # Preferences

        prefs_action = QtGui.QAction('Preferences', self)
        prefs_action.triggered.connect(lambda: self.onEditPreferences(True))
        prefs_action.setShortcut(QtGui.QKeySequence.Preferences)
        help_menu.addAction(prefs_action)

        # Documentation

        doc_action = QtGui.QAction('Documentationt', self)
        doc_action.triggered.connect(self.onDoc)
        help_menu.addAction(doc_action)

        # Console

        # console_action = QtGui.QAction('Console', self)
        # console_action.triggered.connect(self.show_console)
        # help_menu.addAction(console_action)

        if sys.platform == 'darwin':
            self.menuBar().setNativeMenuBar(
                False)  # this put the menu in the  #  window itself in OSX, as in windows.  # TODO: set this in
            # preferences

        self.preference_pages.extend([GeneralPreferencesWidget, ])

        # --------------------------------------------------------------------------------------------------------------
        # Signal connections
        # --------------------------------------------------------------------------------------------------------------

        # user requests
        self.projectwidget.sigDatasetSelected.connect(self.project.onSelectDataset)
        self.projectwidget.sigDatasetAdded.connect(self.project.addDataset)
        self.projectwidget.sigDatasetRemoved.connect(self.project.removeDataset)

        # model changes
        self.project.sigProjectChanged.connect(self.controller.onProjectChanged)
        self.project.sigDatasetChanged.connect(self.controller.onDatasetChanged)

        # --------------------------------------------------------------------------------------------------------------
        # Show window
        # --------------------------------------------------------------------------------------------------------------

        if show:
            self.show()
            self.controller.onProjectChanged('opened')

    # ..................................................................................................................
    def setupPlot(self, title=None):

        # Create the plotwidget, if it doesn't exist yet.
        if not hasattr(self, 'plotwidget'):
            self.plotwidget = plotwidget = PlotWidget(parent=self)
            self.dplot.addWidget(plotwidget)

        # Update dock name
        self.plotwidget.show()
        if title is not None:
            self.dplot.setTitle(title)
            self.dplot.showTitleBar()

    # ..................................................................................................................
    def getVersion(self):
        """
        Returns current version of the GUI application.
        """
        return get_version(root='..', relative_to=__file__)

    # ..................................................................................................................
    def onAbout(self):

        about = QtGui.QMessageBox.about(self, "About SpectroChemPy",
        f""" 
        <center>
        <strong> SpectroChemPy GUI Info </strong><br/>
        <strong>GUI Version:</strong> {self.getVersion()}<br>
        <strong>API Version:</strong> {scp.version}<br>
        <strong>Authors:</strong> Christian Fernandez and Arnaud Travert<br>
        <strong>License:</strong> MIT Licence<br>
        <br/>

        <p><strong>SpectroChemPy</strong> is a framework for processing, analysing and modelling
         <strong>Spectro</>scopic data for <strong>Chem</strong>istry with <strong>Py</strong>thon.
         It is a cross platform software, running on Linux, Windows or OS X.</p><br><br>
        
        <div class='warning'> SpectroChemPy is still experimental and under active development. Its current design and
         functionalities are subject to major changes, reorganizations, bugs and crashes!!!. Please report any issues
        to the <a url='https://github.com/spectrochempy/spectrochempy/issues'>Issue Tracker<a>
        </div><br><br>
        When using <strong>SpectroChemPy</strong> for your own work, you are kindly requested to cite it this way:
        <pre>Arnaud Travert & Christian Fernandez, SpectroChemPy, a framework for processing, analysing and modelling of
        Spectroscopic data for Chemistry with Python https://www.spectrochempy.fr, (version {scp.version})
        Laboratoire Catalyse and Spectrochemistry, ENSICAEN/University of Caen/CNRS, 2021
        </pre></p>

        </center>

        """)  # % versions)

    # ..................................................................................................................
    def onEditPreferences(self):

        if hasattr(self, 'preferences'):
            try:
                self.preferences.close()
            except RuntimeError:
                pass
        self.preferences = dlg = Preferences(self)

        for Page in self.preference_pages:
            page = Page(dlg)
            page.initialize()
            dlg.add_page(page)

        if exec_:
            dlg.exec_()

    def onDoc(self):

        pass # Not implemented yet

    # ..................................................................................................................
    def onShowConsole(self):
        """
        Not yet implemented
        """
        self.statusbar.showMessage('Sorry, Console is not yet implemented.')
