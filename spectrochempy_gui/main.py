# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

import sys
from os import environ

# Environment variable SCPY_GUI must be set before importing spectrochempy (imported with MainWindow) to inform it
# that we are running into a GUI
environ['SCPY_GUI'] = "RUNNING"

#..................................................................................................................
def start():

    # Main thread
    from spectrochempy_gui.pyqtgraph.Qt import QtGui
    from spectrochempy_gui.gui import MainWindow

    gui = QtGui.QApplication(sys.argv)
    mw = MainWindow(show=True)
    gui.exec_()

    # Quit
    gui.quit()

# ======================================================================================================================
if __name__ == '__main__':

    start()

    # Remove the environment variable
    del environ['SCPY_GUI']
