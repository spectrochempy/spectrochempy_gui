# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================
from functools import partial
import re

import numpy as np
from matplotlib import pyplot as plt

import spectrochempy as scp

from spectrochempy_gui import pyqtgraph as pg
from spectrochempy_gui.pyqtgraph.Qt import QtCore, QtGui
from spectrochempy_gui.pyqtgraph.functions import mkPen, mkColor
from spectrochempy_gui.pyqtgraph import GraphicsLayoutWidget, ViewBox

# ----------------------------------------------------------------------------------------------------------------------
class CustomViewBox(ViewBox):
    """
    Subclass of ViewBox
    """
    sigPlotModeChanged = QtCore.Signal(object)
    sigColorMapChanged = QtCore.Signal(object)
    sigLineWidthChanged = QtCore.Signal(object)

    signalShowT0 = QtCore.Signal()
    signalShowS0 = QtCore.Signal()

    def __init__(self, parent=None, ndim=1, prefs=None):
        """
        Constructor of the CustomViewBox
        """
        super().__init__(parent)

        self.ndim = ndim
        self.prefs = prefs

        self.setRectMode()          # Set mouse mode to rect for convenient zooming
        self.menu = None            # Override pyqtgraph ViewBoxMenu
        self.menu = self.getMenu()  # Create the menu

    def raiseContextMenu(self, ev):
        """
        Raise the context menu
        """
        if not self.menuEnabled():
            return
        menu = self.menu # getMenu()
        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))

    def getMenu(self):
        """
        Create the menu
        """
        if self.menu is None:
            self.menu = QtGui.QMenu()

        self.PlotModeMenu = QtGui.QMenu("Plot mode")
        self.plotModeCombo = QtGui.QComboBox()
        self.modeItems = ['pen', 'scatter', 'scatter+pen', 'bar'] if self.ndim < 2 else ['stack', 'map', 'image',
                                                                                      'surface']
        self.plotModeCombo.insertItems(1,self.modeItems)
        self.plotModeCombo.activated.connect(self.emitPlotModeChanged)
        self.plotModeAction = QtGui.QWidgetAction(None)
        self.plotModeAction.setDefaultWidget(self.plotModeCombo)
        self.PlotModeMenu.addAction(self.plotModeAction)
        self.menu.addMenu(self.PlotModeMenu)

        if self.ndim == 2:
            self.ColorMapMenu = QtGui.QMenu("Colormap")
            self.colorMapCombo = QtGui.QComboBox()
            self.colorMapItems = plt.colormaps()
            self.colorMapCombo.insertItems(1,self.colorMapItems)
            self.colorMapCombo.setCurrentIndex(self.colorMapItems.index(self.prefs.colormap))
            self.colorMapCombo.activated.connect(self.emitColorMapChanged)
            self.colorMapAction = QtGui.QWidgetAction(None)
            self.colorMapAction.setDefaultWidget(self.colorMapCombo)
            self.ColorMapMenu.addAction(self.colorMapAction)
            self.menu.addMenu(self.ColorMapMenu)

        self.LineMenu = QtGui.QMenu("Linewidth")
        self.lineSpinBox = pg.SpinBox(value=1, step=0.1, decimals=3)
        self.lineSpinBox.sigValueChanged.connect(self.emitLineWidthChanged)
        self.lineAction = QtGui.QWidgetAction(None)
        self.lineAction.setDefaultWidget(self.lineSpinBox)
        self.LineMenu.addAction(self.lineAction)
        self.menu.addMenu(self.LineMenu)

        self.viewAll = QtGui.QAction("Zoom reset", self.menu)
        self.viewAll.triggered.connect(self.autoRange)
        self.menu.addAction(self.viewAll)

        self.leftMenu = QtGui.QMenu("Left mouse click mode")
        group = QtGui.QActionGroup(self)
        pan = QtGui.QAction(u'Pan', self.leftMenu)
        zoom = QtGui.QAction(u'Zoom', self.leftMenu)
        self.leftMenu.addAction(pan)
        self.leftMenu.addAction(zoom)
        pan.triggered.connect(self.setPanMode)
        zoom.triggered.connect(self.setRectMode)
        pan.setCheckable(True)
        zoom.setCheckable(True)
        pan.setActionGroup(group)
        zoom.setActionGroup(group)
        self.menu.addMenu(self.leftMenu)

        self.menu.addSeparator()

        self.showT0 = QtGui.QAction(u'Afficher les marqueurs d\'amplitude', self.menu)
        self.showT0.triggered.connect(self.emitShowT0)
        self.showT0.setCheckable(True)
        self.showT0.setEnabled(False)
        self.menu.addAction(self.showT0)
        self.showS0 = QtGui.QAction(u'Afficher les marqueurs de Zone d\'intÃ©gration', self.menu)
        self.showS0.setCheckable(True)
        self.showS0.triggered.connect(self.emitShowS0)
        self.showS0.setEnabled(False)
        self.menu.addAction(self.showS0)

        return self.menu

    def emitLineWidthChanged(self, val):
        self.sigLineWidthChanged.emit(float(val.value()))

    def emitPlotModeChanged(self, index):
        mode = self.modeItems[index]
        self.sigPlotModeChanged.emit(mode)

    def emitColorMapChanged(self, index):
        color = self.colorMapItems[index]
        self.sigColorMapChanged.emit(color)

    def emitShowT0(self):
        """
        Emit signalShowT0
        """
        self.signalShowT0.emit()

    def emitShowS0(self):
        """
        Emit signalShowS0
        """
        self.signalShowS0.emit()

    def setRectMode(self):
        """
        Set mouse mode to rect
        """
        self.setMouseMode(self.RectMode)

    def setPanMode(self):
        """
        Set mouse mode to pan
        """
        self.setMouseMode(self.PanMode)

# --------------------------------------------------------------------
# Plot widget
# --------------------------------------------------------------------

class PlotWidget(GraphicsLayoutWidget):

    _dataset = None  # current dataset associated to the plotwidget

    # ..................................................................................................................
    def __init__(self, parent):

        # Use the Qt's GraphicsView framework offered by Pyqtgraph
        super().__init__(title='')

        self.parent = parent

        # Prepare additionnal traces
        self.selected = None  # traces selected in 2D spectra
        self.selected_pen = None # original pen of a selected curve

    # ..................................................................................................................
    def _masked(self, data, mask):
        """
        Utility function which returns a masked array.
        """
        if self._dataset is None:
            return None

        if not np.any(mask):
            mask = np.zeros(data.shape).astype(bool)
        data = np.ma.masked_where(mask, data)  # np.ma.masked_array(data, mask)
        return data

    # ..................................................................................................................
    @property
    def dataset(self):
        """
        Returns the current dataset
        """
        return self._dataset

    # ..................................................................................................................
    @dataset.setter
    def dataset(self, val):
        """
        Set the current dataset.
        """
        self._dataset = val

    # ..................................................................................................................
    @property
    def data(self):
        """
        Returns the current dataset masked data.
        """
        # z intensity (by default we plot real component of the data)

        return self._masked(np.real(self._dataset.data), self._dataset.mask)

    # ..................................................................................................................
    @property
    def processeddata(self):
        """
        Returns processeddata with the same mask as the original dataset.
        """
        if self._dataset.processeddata is None:
            return None
        return self._masked(np.real(self._dataset.processeddata), self._dataset.processedmask)

    # ..................................................................................................................
    @property
    def baselinedata(self):
        """
        Returns baselinedata with the same mask as the original dataset.
        """
        if self._dataset.baselinedata is None:
            return None
        return self._masked(np.real(self._dataset.baselinedata), self._dataset.mask)

    # ..................................................................................................................
    @property
    def referencedata(self):
        """
        Returns referencedata with the same mask as the original dataset.
        """
        if self._dataset.referencedata is None:
            return None
        return self._masked(np.real(self._dataset.referencedata), self._dataset.mask)

#..................................................................................................................
    def draw_regions(self):

        procs = self.parent.controller.params.param('processing').children()
        for proc in procs:
            if proc.name().startswith('define regions'):
                kind = proc.param('kind').value()
                if kind == 'undefined' or not hasattr(proc, 'regions'):
                    return
                for el, par in proc.regions.regionItems.values():
                    if el._name.startswith(kind):
                        if not proc.opts['expanded']:
                            self.p.removeItem(el)
                        else:
                            self.p.addItem(el, ignoreBounds=True)

    # ..................................................................................................................
    def changeColorMap(self, map):
        self.dataset.meta['colormap'] = map
        self.draw(self.dataset)

    def changePlotMode(self, mode):
        self.dataset.meta['plotmode'] = mode
        self.draw(self.dataset)

    def changeLineWidth(self, lw):
        self.dataset.meta['linewidth'] = lw
        self.draw(self.dataset)

    # ..................................................................................................................
    def draw(self, dataset, zoom_reset=False):
        """
        Draw 1D or 2D dataset corresponding to the current dataset.

        Parameters
        ----------
        zoom_reset: bool, optional
            True if the x and y range must be reset to the full range when redrawing.
        """

        self.dataset = dataset

        # Create the main plotItem
        if not hasattr(self, 'p'):
            vb = CustomViewBox(ndim=dataset.ndim, prefs=dataset.preferences)
            self.p = self.addPlot(row=0, col=0, viewBox=vb)

        # Draw main data
        scp.debug_('>>>>>>>>>> Draw')
        self._draw(zoom_reset=zoom_reset)

        # Draw processed
        self._draw_processed(zoom_reset=zoom_reset, only_x=True)  # zoom reset only along x but autoscale on y

    # ..................................................................................................................
    def _draw_processed(self, **kwargs):
        # Draw in a second viewbox the processed data.

        if self.dataset.processeddata is None:
            if not hasattr(self, 'proc'):
                return
            else:
                # Try to remove the processing plotItem if it exists
                self.removeItem(self.proc)
                del self.proc
                self.p.setTitle('')
                return

        if not hasattr(self, 'proc'):
            # we have processed data but not yet the corresponding plotItem: create one.
            vb = CustomViewBox(ndim=self.dataset.ndim, prefs=self.dataset.preferences)
            self.proc = self.addPlot(row=1, col=0, title='Processed dataset', viewBox=vb)
            self.p.setTitle('Original dataset')

        self._draw(plotitem=self.proc, processed=True, **kwargs)

        # self.p.vb.register(self.p.titleLabel.text)
        # self.proc.vb.register(self.proc.titleLabel.text)

    def _draw(self, **kwargs):

        # Prepare the viewbox
        plot = kwargs.get('plotitem', self.p)
        vb = plot.vb

        if self.dataset.ndim > 1:
            vb.sigColorMapChanged.connect(self.changeColorMap)
            vb.sigPlotModeChanged.connect(self.changePlotMode)
            vb.sigLineWidthChanged.connect(self.changeLineWidth)
        # Zoom
        zoom_reset = kwargs.get('zoom_reset', False)
        only_x = kwargs.get('only_x', False)
        zoomx = False
        if plot.getAxis('bottom').range != [0,1] and not zoom_reset:
            zoomx = plot.getAxis('bottom').range
        zoomy = False
        if plot.getAxis('left').range != [0,1] and not zoom_reset and not only_x:
            zoomy = plot.getAxis('left').range
        plot.clear()

        # Copy the dataset
        new = self.dataset.copy()
        processed = kwargs.get('processed', False)
        if processed :
            zdata = self.processeddata
        else:
            zdata = self.data

        # Get some preferences
        prefs = new.preferences

        lw = new.meta.get('linewidth', prefs.lines_linewidth)

        # Set axis
        # ========

        # set the abscissa axis
        # ---------------------

        # the actual dimension name is the last in the new.dims list
        dimx = new.dims[-1]

        # reduce data to the ROI
        x = getattr(new, dimx)
        lx, ux = x.roi
        if new.ndim > 1:
            new = new[:, lx:ux]
        else:
            new = new[lx:ux]

        x = getattr(new, dimx)
        if x is not None and x.implements('CoordSet'):
            # if several coords, take the default ones:
            x = x.default
        xsize = new.shape[-1]
        show_x_points = False
        if x is not None and hasattr(x, 'show_datapoints'):
            show_x_points = x.show_datapoints
        if show_x_points:
            # remove data and units for display
            x = scp.LinearCoord.arange(xsize)

        discrete_data = False

        if x is not None and (not x.is_empty or x.is_labeled):
            xdata = x.data
            if not np.any(xdata):
                if x.is_labeled:
                    discrete_data = True
                    # take into account the fact that sometimes axis have just labels
                    xdata = range(1, len(x.labels) + 1)
        else:
            xdata = range(xsize)

        xl = [xdata[0], xdata[-1]]
        xl.sort()

        xlim = list(kwargs.get('xlim', xl))
        xlim.sort()
        xlim[-1] = min(xlim[-1], xl[-1])
        xlim[0] = max(xlim[0], xl[0])

        if kwargs.get('x_reverse', kwargs.get('reverse', x.reversed if x else False)):
            # xlim.reverse()
            vb.invertX()

        if zoomx:
            vb.setXRange(*zoomx, padding=0)
        else:
            vb.setXRange(*xlim, padding=0)

        ndim = new._squeeze_ndim

        if ndim > 1:

            # set the ordinates axis
            # ----------------------

            # the actual dimension name is the second in the new.dims list
            dimy = new.dims[-2]

            # reduce to ROI
            y = getattr(new, dimy)
            ly, uy = y.roi
            new = new[ly:uy]

            y = getattr(new, dimy)
            if y is not None and y.implements('CoordSet'):
                # if several coords, take the default ones:
                y = y.default
            ysize = new.shape[-2]

            show_y_points = False
            if ysize > 1:

                # 2D (else it will be displayed as 1D)
                # ------------------------------------
                if y is not None and hasattr(y, 'show_datapoints'):
                    show_y_points = y.show_datapoints
                if show_y_points:
                    # remove data and units for display
                    y = scp.LinearCoord.arange(ysize)

                if y is not None and (not y.is_empty or y.is_labeled):
                    ydata = y.data

                    if not np.any(ydata):
                        if y.is_labeled:
                            ydata = range(1, len(y.labels) + 1)
                else:
                    ydata = range(ysize)

                yl = [ydata[0], ydata[-1]]
                yl.sort()

                ylim = list(kwargs.get("ylim", yl))
                ylim.sort()
                ylim[-1] = min(ylim[-1], yl[-1])
                ylim[0] = max(ylim[0], yl[0])

        zlim = kwargs.get('zlim', (np.ma.min(zdata), np.ma.max(zdata)))

        method = new.meta.get('mode', prefs.method_2D) if ndim > 1 else 'stack'

        if method in ['stack']:  # For 2D and 1D plot

            # the z axis info
            # ---------------
            # zl = (np.min(np.ma.min(ys)), np.max(np.ma.max(ys)))
            amp = 0  # np.ma.ptp(zdata) / 50.
            zl = (np.min(np.ma.min(zdata) - amp), np.max(np.ma.max(zdata)) + amp)
            zlim = list(kwargs.get('zlim', zl))
            zlim.sort()
            z_reverse = kwargs.get('z_reverse', False)
            if z_reverse:
                vb.invertY()

            # set the limits
            # ---------------

            # if yscale == "log" and min(zlim) <= 0:
            #    # set the limits wrt smallest and largest strictly positive values
            #    ax.set_ylim(10 ** (int(np.log10(np.amin(np.abs(zdata)))) - 1),
            #                10 ** (int(np.log10(np.amax(np.abs(zdata)))) + 1))
            #else:
            if zoomy:
                vb.setYRange(*zoomy, padding=0)
            else:
                vb.setYRange(*zlim, padding=0)

        else:

            #TODO
            pass # not implemented

            # # the y axis info
            # # ----------------
            # # if data_only:
            # #    ylim = ax.get_ylim()
            #
            # ylim = list(kwargs.get('ylim', ylim))
            # ylim.sort()
            # y_reverse = kwargs.get('y_reverse', y.reversed if y else False)
            # if y_reverse:
            #     ylim.reverse()
            #
            # # set the limits
            # # ----------------
            # ax .set_ylim(ylim)


        # Log scale

        # yscale = kwargs.get("yscale", "linear")
        # ax.set_yscale(yscale)
        # xscale = kwargs.get("xscale", "linear")
        # ax.set_xscale(xscale)  # , nonpositive='mask')

        # Plot the dataset
        # ================

        #  ax.grid(prefs.axes_grid)  # TODO

        if ndim > 1:
            normalize = kwargs.get('normalize', None)
            cmap = new.meta.get('colormap', prefs.colormap)
            self.cmap = pg.colormap.get(cmap, source='matplotlib', skipCache=True)

        if method in ['stack']:

            # if data.ndim == 1:
            #    data = data.at_least2d()

            ncurves = zdata.shape[0]
            if ncurves > 1:
                colors = self.cmap.color
                icolor = np.linspace(0, (colors.shape[0]-1), ncurves).astype(int)
                colors = colors[icolor]
            else:
                colors = [prefs('color')]
            self.colors = colors

            # self.curves = []
            if hasattr(zdata, 'mask'):
                mask = zdata.mask
                zdata[mask] = 0

            # downsampling
            step = 1
            if ncurves > 500:
                step = int(ncurves / 500)

            for i in np.arange(0, ncurves, step):
                c = pg.PlotCurveItem(
                          x=xdata,
                          y=zdata[i:i+step].max(axis=0) if step > 1 else zdata[i],
                          pen=mkPen(mkColor(colors[i]), width=lw),
                          clickable=True
                          )
                plot.addItem(c)
                c.sigClicked.connect(partial(self._curveSelected, plot))

        # display a title
        # ----------------
        title = kwargs.get('title', None)
        if title:
            plot.setTitle(title)
        elif kwargs.get('plottitle', False):
            plot.setTitle(new.name)

        # labels
        # ------
        def make_label(ss, label):
            if ss.units is not None and str(ss.units) != 'dimensionless':
                units = r"{:~P}".format(ss.units)
            else:
                units = ''
            label = f"{label} / {units}"
            return label

        # x label
        # -------
        xlabel = kwargs.get("xlabel", None)
        if show_x_points:
            xlabel = 'data points'
        if not xlabel:
            xlabel = make_label(x, x.title)

        plot.setLabel('bottom', text=xlabel)

        # uselabelx = kwargs.get('uselabel_x', False)
        # if x and x.is_labeled and (uselabelx or not np.any(x.data)) and len(x.labels) < number_x_labels + 1:
        #     # TODO refine this to use different orders of labels
        #     ax.set_xticks(xdata)
        #     ax.set_xticklabels(x.labels)
        #

        if ndim > 1:
            # y label
            # --------
            ylabel = kwargs.get("ylabel", None)
            if show_y_points:
                ylabel = 'data points'
            if not ylabel:
                if method in ['stack']:
                    ylabel = make_label(new, y.title)
                else:
                    ylabel = make_label(y, new.dims[-2])

            # uselabely = kwargs.get('uselabel_y', False)
            # if y and y.is_labeled and (uselabely or not np.any(y.data)) and len(y.labels) < number_y_labels:
            #             # TODO refine this to use different orders of labels
            #             ax.set_yticks(ydata)
            #             ax.set_yticklabels(y.labels)

        # z label
        # -------
        zlabel = kwargs.get("zlabel", None)
        if not zlabel:
            if method in ['stack']:
                zlabel = make_label(new, new.title)
            elif method in ['surface']:
                zlabel = make_label(new, 'values')
            plot.setLabel('left', text=zlabel)
        else:
            zlabel = make_label(new, 'z')

        if method in ['stack']:
            # do we display the ordinate axis?
            if kwargs.get('show_y', True):
                plot.setLabel('left', text=zlabel)
            else:
                plot.hideAxis('left')

        label = pg.LabelItem(parent=vb, justify='left')

        # --------------------------------------------------------------------------------------------------------------
        # regions
        # --------------------------------------------------------------------------------------------------------------

        # restore regions
        if plot == self.p:
            self.draw_regions()

        # --------------------------------------------------------------------------------------------------------------
        # vertical line
        # --------------------------------------------------------------------------------------------------------------

        vLine = pg.InfiniteLine(angle=90, movable=False)
        # hLine = pg.InfiniteLine(angle=0, movable=False)
        plot.addItem(vLine, ignoreBounds=True)
        # plot.addItem(hLine, ignoreBounds=True)

        scene = plot.scene()
        def mouseMoved(evt):
            pos = evt
            scene.blockSignals(True)
            if plot.sceneBoundingRect().contains(pos):
                mouse_point = vb.mapSceneToView(pos)
                coord = mouse_point.x()
                ll, hl = vb.state['viewRange'][0]
                lld, hld = x.roi
                if max(ll, lld) <= coord <= min(hl, hld):
                    ds = new[:, float(coord)]
                    vLine.setVisible(True)
                    if self.selected:
                        try:
                            # corresponding x index
                            index = x.loc2index(coord)
                            z = self.selected.yData[index] * x.units
                            zstr = f'{z:~0.2fP} '

                        except Exception:
                            vLine.setVisible(False)
                            scene.blockSignals(False)
                            return   # out of limits
                    else:
                        z = ds.value
                        zstr = f'{z:~0.2fP} '
                    if z.size > 1:
                        # mode than one element (2D)
                        z = z.squeeze()
                        zstr = f'{z.min():~0.2fP} -- {z.max():~0.2fP} '

                    coord = coord * x.units
                    coordstr = f'{coord:~0.2fP}'

                    label.setText(
                            f"<span style='background-color:#FFF; font-size: 12pt'>"
                            f"<span style='color: blue'>{x.title} = {coordstr}</span>"
                            f"<br/>"
                            f"<span style='color: green'>{ds.title} = {zstr}</span>"
                            f"</span>")
                    vLine.setPos(mouse_point.x())
                    # hLine.setPos(mouse_point.y())
                else:
                    label.setText('')
                    vLine.setPos(0)
                    vLine.setVisible(False)
                    # hLine.setPos(0)
            scene.blockSignals(False)

        plot.scene().sigMouseMoved.connect(mouseMoved)

    def _findCurveIndex(self, plot, curve):

        for index, c in enumerate(plot.curves):
            if not isinstance(c, pg.PlotCurveItem):
                continue
            if c is curve:
                break

        return index

    def _curveSelected(self, plot, curve):
        # Action when a curve is selected

        lw =  self.dataset.meta.get('linewidth', self.dataset.preferences.lines_linewidth)
        if self.dataset._squeeze_ndim < 2:
            return

        if self.selected is not None:
            # reset previous
            #index = self._findCurveIndex(plot, self.selected)
            pen = self.selected_pen
            self.selected.setPen(pen)

        if curve != self.selected:
            # set new selected
            self.selected_pen = curve.opts['pen']
            curve.setPen('k', width=lw*3)
            self.selected = curve

        else:
            # index = self._findCurveIndex(plot, curve)
            curve.setPen(self.selected_pen)
            self.selected = None
