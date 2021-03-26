# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================


from pathlib import Path
from spectrochempy_gui.pyqtgraph.Qt import QtWidgets


# ----------------------------------------------------------------------------------------------------------------------
def geticon(name="scpy.png"):

    return Path(__file__).parent / "ressources" / name


# ----------------------------------------------------------------------------------------------------------------------
def confirm_msg(parent, caption, msg):
    """
    Display a message box to confirm an action.
    """
    reply = QtWidgets.QMessageBox.question(parent,
                                           caption,
                                           msg,
                                           QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                           QtWidgets.QMessageBox.No)
    return reply == QtWidgets.QMessageBox.Yes


# ----------------------------------------------------------------------------------------------------------------------
def info_msg(parent, caption, msg):
    """
    Display a message box to give information.
    """
    if caption == 'Warning':
        QtWidgets.QMessageBox.warning(parent, caption, msg)
    else:
        QtWidgets.QMessageBox.information(parent, caption, msg)
    return
