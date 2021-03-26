# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

from functools import partial
import spectrochempy as scp
from spectrochempy_gui.pyqtgraph.Qt import QtGui, QtCore
from spectrochempy_gui.utils import geticon, confirm_msg

__all__ = ['ProjectTreeWidget']

# ----------------------------------------------------------------------------------------------------------------------
class ProjectTreeWidget(QtGui.QTreeWidget):
    """
    Widget for displaying spectrochempy projects
    """
    # current project
    project = None
    # signals
    sigDatasetAdded = QtCore.Signal()
    sigDatasetRemoved = QtCore.Signal(object)
    sigDatasetSelected = QtCore.Signal(object)

    # ..................................................................................................................
    def __init__(self, parent=None, project=None, showHeader=True):
        """
        Parameters
        ----------
        parent : object
        project : SpectroChemPy Project object
        """
        QtGui.QTreeWidget.__init__(self)
        self.parent = parent
        self.setVerticalScrollMode(self.ScrollPerPixel)
        self.setColumnCount(3)
        self.setHeaderLabels(['name', 'type', 'id'])
        self.setHeaderHidden(not showHeader)
        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.setSortingEnabled(False)
        self.setProject(project)
        self.clicked.connect(self.emitSelectDataset)

    # ..................................................................................................................
    def setProject(self, project):
        """
        Parameters
        ----------
        project: SpectroChemPy project object
        """
        self.clear()
        self.project = project
        self.buildTree(project, self.invisibleRootItem())
        self.expandToDepth(3)
        self.resizeColumnToContents(0)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenuEvent)

    # ..................................................................................................................
    def buildTree(self, obj, parent, name=''):
        if obj is None:
            node = QtGui.QTreeWidgetItem(['No project', ''])
            parent.addChild(node)
            return
        typeStr, id = obj.id.split('_')  # type(obj).__name__
        if typeStr == 'Project':
            name = obj.name
            id = ' '
        node = QtGui.QTreeWidgetItem([name, typeStr, id])
        parent.addChild(node)
        if typeStr == 'Project':
            for k in obj.allnames:
                self.buildTree(obj[k], node, k)
            node.setIcon(0, QtGui.QIcon(str(geticon('folder.png'))))
        elif typeStr == 'NDDataset':
            node.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)  # QtCore.Qt.ItemIsUserCheckable |
            # node.setCheckState(1, QtCore.Qt.Unchecked)
            node.setIcon(0, QtGui.QIcon(str(geticon('file.png'))))
        else:
            return

    # ..................................................................................................................
    def showContextMenuEvent(self, event):
        self.contextMenu = QtGui.QMenu()
        # Infos about the selected node.
        index = self.indexAt(event)
        if not index.isValid():
            return
        item = self.itemAt(event)
        name = item.text(0)
        if item.text(1) == 'Project':
            # self.contextMenu.addAction('Rename').triggered.connect(partial(self.editname, item))
            self.contextMenu.addAction('Add new dataset').triggered.connect(self.emitAddDataset)
        if name != self.project.name:
            # can't remove the top element without cloing the project
            self.contextMenu.addAction('Remove').triggered.connect(partial(self.emitRemove, item))
        self.contextMenu.popup(self.mapToGlobal(event))

    # ..................................................................................................................
    def editname(self, *args):
        # TODO: editing name
        scp.debug_(args)

    def emitAddDataset(self):
        self.sigDatasetAdded.emit()

    def emitRemove(self, sel=None):
        if sel is None or sel.text(0) == self.project.name:
            scp.warning_('No item selected. Please select one to remove.')
            return
        name = sel.text(0)
        self.sigDatasetRemoved.emit(name)

    # ..................................................................................................................
    def emitSelectDataset(self, *args, **kwargs):
        """
        When an item is clicked in the project window, some actions can be
        performed, e.g., plot the corresponding data.

        """
        sel = self.currentItem()
        if sel:
            # make a plot of the data
            id = sel.text(2)
            name = sel.text(0)
            if sel.text(1) == "Project":
                if name == self.project.name:
                    return
                name = f'{name}/original'
            scp.debug_(f'---------------------- Dataset {name}({id}) selected')
            self.sigDatasetSelected.emit(name)
