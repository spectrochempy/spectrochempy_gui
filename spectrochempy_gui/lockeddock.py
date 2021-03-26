# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

"""
Dock and dockaea objects in replacement of pyqtgraph docks.
"""

from spectrochempy_gui.pyqtgraph.dockarea import DockArea, Dock

__all__ = ['LockedDockArea', 'LockedDock']

# ======================================================================================================================
class LockedDock(Dock):

    # This class is used to eliminate a standard Dock class' ability to detach and move (i.e. dragging this Dock
    # will have no effect)

    def __init__(self, name, area=None, size=(10, 10), widget=None, hideTitle=False, autoOrientation=True,
                 closable=False, fontSize="12px"):

        # Initialize the baseclass
        #
        Dock.__init__(self, name, area, size, widget, hideTitle, autoOrientation, closable, fontSize)

        # Override the label's double click event of pyqtgraph. Normally double clicking the dock's label will cause
        # it to detach into it's own window.
        self.label.mouseDoubleClickEvent=self.noopEvent

        self.moveLabel = False
        self.setMinimumSize(300,50)

    # ..................................................................................................................
    def dragEventEnter(self, ev):
        pass

    # ..................................................................................................................
    def dragMoveEvent(self, ev):
        pass

    # ..................................................................................................................
    def dragLeaveEvent(self, ev):
        pass

    # ..................................................................................................................
    def dragDropEvent(self, ev):
        pass

    # ..................................................................................................................
    def noopEvent(self,ev):
        pass


# ======================================================================================================================
class LockedDockArea(DockArea):

    # ..................................................................................................................
    def dragEventEnter(self, ev):
        pass

    # ..................................................................................................................
    def dragMoveEvent(self, ev):
        pass

    # ..................................................................................................................
    def dragLeaveEvent(self, ev):
        pass

    # ..................................................................................................................
    def dragDropEvent(self, ev):
        pass
