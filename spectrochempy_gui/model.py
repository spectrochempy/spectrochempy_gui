# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

"""
Model module.

"""
from functools import partial
from pathlib import Path

import spectrochempy as scp

from spectrochempy_gui import pyqtgraph as pg
from spectrochempy_gui.pyqtgraph.Qt import QtGui, QtCore
from spectrochempy_gui.utils import confirm_msg

# ----------------------------------------------------------------------------------------------------------------------
class Project(QtCore.QObject):
    """
    Class defining the project model.

    A project contains one or several Dataset objects.

    Parameters
    ----------
    parent: QObject
        A reference to the parent object (in principle it's the Mainwindow of the application).

    """
    sigProjectChanged = QtCore.Signal(object)
    sigSetDirty = QtCore.Signal()
    sigDatasetChanged = QtCore.Signal(object, object)

    _parent = None
    _project = None
    _dataset = None

    _dirty = False

    _directory = scp.preferences.project_directory

    # ..................................................................................................................
    def __init__(self, parent):
        QtCore.QObject.__init__(self)
        self._parent = parent

        # Autosave feature
        self.autosaveTimer = QtCore.QTimer()
        self.autosaveTimer.setInterval(30000)
        self.autosaveTimer.timeout.connect(self.saveProject)

        # Open last_project
        last_project = scp.preferences.last_project
        if last_project:
            last_project = Path(last_project).with_suffix(".pscp")
        if scp.preferences.autoload_project and last_project is not None and last_project.exists():
            scp.debug_(f'Open last project {last_project}')
            self.project = last_project
        else:
            self.openProject(new=True)

    # ..................................................................................................................
    def __call__(self):
        return self.project

    # ------------------------------------------------------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------------------------------------------------------

    @property
    def parent(self):
        return self._parent

    @property
    def project(self):
        return self._project

    @project.setter
    def project(self, fname):
        #self.parent.statusbar.showMessage("Setting a project ... ")
        scp.preferences.last_project = fname
        proj = self._loadProject(fname)
        if proj is not None:
            if not proj.directory:
                proj._directory = self._directory
        self._project = proj
        if scp.preferences.autosave_project:
            self.autosaveTimer.start()
        self.dirty = True
        self.sigProjectChanged.emit('opened')
        #self.parent.statusbar.showMessage("")

    @property
    def dataset(self):
        return self._dataset

    @dataset.setter
    def dataset(self, dataset):
        self._dataset = dataset

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, dirty):
        self._dirty = dirty
        self.sigSetDirty.emit()

    # ------------------------------------------------------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------------------------------------------------------

    # ..................................................................................................................
    def openProject(self, **kwargs):
        """

        Parameters
        ----------
        new: Bool
            If False, open an existing projetc, otherwise create a new one

        """
        if not kwargs.pop('new', False):
            # Open an existing project
            directory = self._directory
            fname = QtGui.QFileDialog.getOpenFileName(self.parent, 'Project file', str(directory),
                                                      'SpectroChemPy project files (*.pscp);;All files (*)')
            fname = fname[0]
            if not fname:
                return
        else:
            # New project
            fname = None
        self.project = fname

    # ..................................................................................................................
    def closeProject(self):
        # Save current project
        self.saveProject()
        self.project = None
        self.dataset = None
        # Stop autosave
        self.autosaveTimer.stop()
        # Signal
        self.sigProjectChanged.emit('closed')

    # ..................................................................................................................
    def saveProject(self, *args, **kwargs):
        if not kwargs.pop('force', False):
            if not self.dirty:
                return
        scp.debug_('Saving project')
        # we need to save only the original data as they will be recalculaded anyway when reloaded
        proj = self.project.copy()
        for name in proj.projects_names:
            for datasetname in proj[name].datasets_names:
                if 'original' not in datasetname:
                    del proj[name][datasetname]
                else:
                    proj[name][datasetname].processeddata = None
                    proj[name][datasetname].processedmask = False
                    if proj[name][datasetname].transposed:
                        proj[name][datasetname].transpose(inplace=True)

        if proj.directory is None:
            proj._directory = self._directory
        if kwargs.get('saveas') or proj.name == 'untitled':
            proj.save_as(self._directory / 'untitled.pscp', Qt_parent=self.parent)
            self.sigProjectChanged.emit('renamed')
        else:
            proj.save()
        scp.preferences.last_project = Path(proj.directory) / proj.name
        self.dirty = False

    # ------------------------------------------------------------------------------------------------------------------
    # Dataset
    # ------------------------------------------------------------------------------------------------------------------

    # ..................................................................................................................
    def addDataset(self, dataset=None):
        scp.debug_('Add a dataset')
        # Read the  dataset
        try:
            if not dataset:
                dataset = scp.read(Qt_parent=self.parent, protocol='omnic')
            if dataset is None:  # still not determined.
                return
        except Exception as e:
            scp.error_(e)

        # Create a subproject with this dataset
        subproj = scp.Project()
        self.project.add_project(subproj, dataset.name)
        subproj.add_dataset(dataset, f'{dataset.name}/original')

        # Signal
        self.dirty = True
        self.sigProjectChanged.emit('dataset added')

    # ..................................................................................................................
    def removeDataset(self, name=None):
        # Confirm
        if '/original' in name:
            name = name.split('/')[0]
            if not confirm_msg(self.parent, 'Remove', f'Removing the main (original) datset will '
                                                      f'remove all other datasets present in `{name}`.\n'
                                                      f'Is-it what you want?'):
                return
        elif not confirm_msg(self.parent, 'Remove', f'Do you really want to remove the `{name}` dataset?'):
            return
        scp.debug_(f'remove: {name}')
        self.sigDatasetChanged.emit(None, 'deselect')
        if name in self.project.projects_names and self.project[name].implements('Project'):
            # its the whole subproject to be removed
            self.project.remove_project(name)
        else:
            try:
                subproject, name = name.split('/')
                subproject.remove_dataset(name)
            except:
                self.project.remove_dataset(name)

        self.dataset = None
        self.dirty = True
        # Signal
        self.sigProjectChanged.emit('dataset removed')

    # ..................................................................................................................
    def updateDataset(self, dataset):
        if 'untitled' not in dataset.name:
            # the parent subproject should be specified
            subproj = dataset.name.split('/')[0]
            if dataset.name in self.project[subproj].datasets_names:
                # In this case just update : but warning the dataset id must be the same the previous one.
                scp.debug_(f'Update dataset: {dataset.name}')
                id = self.project[subproj]._datasets[dataset.name].id
                dataset._id = id
                self.project[subproj]._datasets[dataset.name] = dataset
                if self.dataset.name == dataset.name:
                    self.sigDatasetChanged.emit(dataset, 'updated')
            else:
                scp.debug_(f'Add dataset {dataset.name} to project')
                self.project[subproj].add_dataset(dataset)
                self.sigProjectChanged.emit('dataset added')
                #self.sigDatasetChanged.emit(dataset, 'added')
            self.dirty = True

    # ..................................................................................................................
    def onSelectDataset(self, name):
        if self.dataset is not None and name == self.dataset.name:
            return
        self.dataset = self.project[name]
        # Signal
        self.sigDatasetChanged.emit(self.dataset, 'select')

    # ------------------------------------------------------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------------------------------------------------------

    # ..................................................................................................................
    def _loadProject(self, *args, **kwargs):
        """
        Load a project.
        """
        if len(args)<1:
            return
        fname = args[0]
        proj = None
        if fname is None or fname in ['', 'untitled']:
            # create a void project
            proj = scp.Project(name='untitled')
        else:
            try:
                proj = scp.Project.load(fname, **kwargs)
                proj.meta['project_file'] = fname

            except Exception as e:
                scp.error_(e)
                self.closeProject()
        return proj

# ----------------------------------------------------------------------------------------------------------------------
class Regions(QtCore.QObject):
    """
    Class defining a set of regions on the plot
    """
    kind = 'undefined'
    regionItems = {}

    sigRegionAdded = QtCore.Signal(object, object)
    sigRegionRemoved = QtCore.Signal(object, object)
    sigRegionChanged = QtCore.Signal(object, object)

    # constant
    BRUSH = {'mask': (200, 200, 200, 60), 'baseline': (0, 200, 0, 60), 'integral': (0, 0, 200, 60), }

    # ..................................................................................................................
    def __init__(self, kind='undefined'):

        QtCore.QObject.__init__(self)

        self.kind = kind
        self.brushcolor = self.BRUSH.get(kind.lower(), (254, 0, 0, 60))

    # ..................................................................................................................
    def addRegion(self, param, kind='undefined', span=None):

        # If kind is undfined do nothing
        if kind == 'undefined':
            return

        # kind selected
        self.kind = kind

        # Update param info with provided span or default values
        if span is None and param.value() != 'undefined':
            span = eval(param.value())
        param.setValue(f'{span[0]:.1f}, {span[1]:.1f}')

        # Define
        region = pg.LinearRegionItem(values=span, brush=self.brushcolor)
        region._name = f'{self.kind}_{param.name()}'
        region.setRegion(span)

        self.regionItems[region._name] = (region, param)

        # events
        region.sigRegionChangeFinished.connect(partial(self.regionChanged, param))
        param.sigRemoved.connect(self.regionRemoved)
        param.sigStateChanged.connect(self.change)

        # signal
        self.sigRegionAdded.emit(self, region)

    # ..................................................................................................................
    def getLinearRegions(self, kind):

        regions={}
        for k, el in self.regionItems.items():
            if k.startswith(kind):
                regions[k] = el
        return regions

    # ..................................................................................................................
    def findLinearRegion(self, name, kind):

        name = f'{kind}_{name}'
        return self.getLinearRegions(kind)[name]

    # ..................................................................................................................
    def regionChanged(self, param, region):

        low, high = region.getRegion()
        param.setValue(f'{low:.1f}, {high:.1f}')

        self.sigRegionChanged.emit(self, region)

    # ..................................................................................................................
    def regionRemoved(self, region):

        el, par = self.findLinearRegion(name=region.name(), kind=self.kind)
        del self.regionItems[el._name]
        del el

        self.sigRegionRemoved.emit(self, region)

        # TODO: add a context menu to the LinearRegionItem  with remove entry

    # ..................................................................................................................
    def remove(self):

        for key in list(self.regionItems.keys()):
            region, param =  self.regionItems[key]
            del  self.regionItems[key]
            del region
            self.sigRegionRemoved.emit(self, param)

    # ..................................................................................................................
    def change(self, param, data, info):
        name = param.name()
        if name == 'kind' and data == 'value':
            self.kind = info
            self.brushcolor = self.BRUSH.get(self.kind.lower(), (254, 0, 0, 128))
            # TODO Apply!
