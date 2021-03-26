# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================


"""
Preferences widget
"""
from warnings import warn

import spectrochempy_gui.pyqtgraph as pg

from spectrochempy_gui.pyqtgraph.Qt import QtGui, QtCore
from spectrochempy_gui.utils import geticon

import spectrochempy as scp

class PreferencePage(object):
    """
    The abstract class for the preference pages
    """
    title = None
    icon = None

    def initialize(self):
        raise NotImplementedError

class PreferencesTree(QtGui.QTreeWidget):
    """
    A QTreeWidget that can be used to display SpectroChemPy preferences
    """
    preferences = None
    value_col = 2

    def __init__(self, preferences, *args, **kwargs):
        """
        Parameters
        ----------
        preferences: object
            The object that contains the preferences

        """
        super().__init__(*args, **kwargs)
        self.preferences = preferences

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_menu)
        self.setColumnCount(self.value_col + 1)
        self.setHeaderLabels(['preference keys', '', 'Value'])

    @property
    def top_level_items(self):
        """An iterator over the topLevelItems in this tree"""
        return map(self.topLevelItem, range(self.topLevelItemCount()))

    def initialize(self):
        """
        Fill the items of the Preferences into the tree
        """
        preferences = self.preferences.traits(config=True, gui=True)
        actualpreferences = self.preferences.config[self.preferences.name]

        vcol = self.value_col
        for i, (key, val) in enumerate(sorted(preferences.items())):
            desc = val.help
            info = val.info_text
            try:
                type = val.trait_types
            except AttributeError:
                type = val.__class__

            val = actualpreferences.get(key, val.default_value)
            if str(val) in ['traitlets.Undefined']:
                val = ''
            item = QtGui.QTreeWidgetItem(0)
            item.setText(0, key)
            item.setToolTip(0, f"{key} ({info})")
            item.setIcon(1, QtGui.QIcon(str(geticon('valid.png'))))
            if desc:
                item.setText(vcol, desc)
                item.setToolTip(vcol, desc)
            child = QtGui.QTreeWidgetItem(0)
            item.addChild(child)
            self.addTopLevelItem(item)
            editor = QtGui.QTextEdit(self)
            # set maximal height of the editor to 1 rows
            editor.setMaximumHeight(1.5 * QtGui.QFontMetrics(editor.font()).height())
            editor.setPlainText(str(val))
            self.setItemWidget(child, vcol, editor)
            editor.textChanged.connect(self.validate(item))
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)

    def validate(self, item):
        def func():

            editor = self.itemWidget(item.child(0), self.value_col)
            s = editor.toPlainText()
            try:
                key = item.text(0)
                # expected traits
                try:
                    val = eval(s)
                except Exception as e:
                    val = s
                # validation
                trait = self.preferences.traits()[key]
                val = trait.validate(key, val)

            except Exception as e:
                item.setIcon(1, QtGui.QIcon(str(geticon('invalid.png'))))
                item.setToolTip(1, "Wrong value: %s" % e)
                return

            item.setIcon(1, QtGui.QIcon(str(geticon('valid.png'))))
            setattr(self.preferences, key, val)

        return func

    def open_menu(self, position):
        menu = QtGui.QMenu()
        expand_all_action = QtGui.QAction('Expand all', self)
        expand_all_action.triggered.connect(self.expandAll)
        menu.addAction(expand_all_action)
        collapse_all_action = QtGui.QAction('Collapse all', self)
        collapse_all_action.triggered.connect(self.collapseAll)
        menu.addAction(collapse_all_action)
        menu.exec_(self.viewport().mapToGlobal(position))

class preferencesWidget(PreferencePage, QtGui.QWidget):

    preferences = None  # implemented in subclass
    tree = None

    @property
    def icon(self):
        return QtGui.QIcon(geticon('preferences.png'))

    def __init__(self, *args, **kwargs):
        super(preferencesWidget, self).__init__(*args, **kwargs)
        self.vbox = vbox = QtGui.QVBoxLayout()

        self.description = QtGui.QLabel(
            '<p>Modify the configuration for your need. '
            'Changes will be applied if they are valid according to the '
            'type of the parameter</p>', parent=self)
        vbox.addWidget(self.description)
        self.tree = tree = PreferencesTree(self.preferences, parent=self)
        vbox.addWidget(self.tree)
        self.setLayout(vbox)

    def initialize(self, configuration=None, validators=None, descriptions=None):
        self.tree.initialize()

class GeneralPreferencesWidget(preferencesWidget):

    preferences = scp.preferences
    title = 'General preferences'


# class PlotPreferencesWidget(preferencesWidget):
#
#     preferences = scp.plot_preferences
#     title = 'Plotting preferences'


class Preferences(QtGui.QDialog):
    """Preferences dialog"""

    def __init__(self, main=None):
        super().__init__(parent=main)
        self.setWindowTitle('Preferences')

        # Widgets
        self.pages_widget = QtGui.QStackedWidget()
        self.contents_widget = QtGui.QListWidget()

        self.bt_reset = QtGui.QPushButton('Reset to defaults')
        self.bbox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Preferences')
        self.contents_widget.setMovement(QtGui.QListView.Static)
        self.contents_widget.setSpacing(1)
        self.contents_widget.setCurrentRow(0)

        # Layout
        hsplitter = QtGui.QSplitter()
        hsplitter.addWidget(self.contents_widget)
        hsplitter.addWidget(self.pages_widget)
        hsplitter.setStretchFactor(1, 1)

        btnlayout = QtGui.QHBoxLayout()
        btnlayout.addStretch(1)
        btnlayout.addWidget(self.bt_reset)
        btnlayout.addWidget(self.bbox)

        vlayout = QtGui.QVBoxLayout()
        vlayout.addWidget(hsplitter)
        vlayout.addLayout(btnlayout)

        self.setLayout(vlayout)

        # Signals
        self.bbox.accepted.connect(self.accept)
        self.bt_reset.clicked.connect(scp.reset_preferences)
        self.pages_widget.currentChanged.connect(self.current_page_changed)
        self.contents_widget.currentRowChanged.connect(self.pages_widget.setCurrentIndex)

    def current_page_changed(self, index):
        self.get_page(index)

    def get_page(self, index=None):
        if index is None:
            widget = self.pages_widget.currentWidget()
        else:
            widget = self.pages_widget.widget(index)
        return widget.widget()

    def accept(self):
        QtGui.QDialog.accept(self)

    def add_page(self, widget):
        scrollarea = QtGui.QScrollArea(self)
        scrollarea.setWidgetResizable(True)
        scrollarea.setWidget(widget)
        self.pages_widget.addWidget(scrollarea)
        item = QtGui.QListWidgetItem(self.contents_widget)
        try:
            item.setIcon(widget.icon)
        except TypeError:
            pass
        item.setText(widget.title)
        item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item.setSizeHint(QtCore.QSize(0, 25))
