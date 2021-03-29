# -*- coding: utf-8 -*-

# ======================================================================================================================
#  Copyright (©) 2015-2021 LCS - Laboratoire Catalyse et Spectrochimie, Caen, France.
#  CeCILL-B FREE SOFTWARE LICENSE AGREEMENT - See full LICENSE agreement in the root directory
# ======================================================================================================================

"""
Controller module.

"""
from functools import partial
from importlib import import_module
from collections import OrderedDict

import yaml
import numpy as np

import spectrochempy as scp

from spectrochempy_gui.pyqtgraph.parametertree import (Parameter, ParameterTree, parameterTypes, registerParameterType)
from spectrochempy_gui.utils import info_msg
from spectrochempy_gui.model import Regions


# ----------------------------------------------------------------------------------------------------------------------
def getProcessors(key='processing'):
    """
    Read processor informations from a yaml file.

    """
    with open('processors.yaml') as f:
        procs = yaml.load(f, Loader=yaml.FullLoader)

    for k, v in procs[key].items():
        v.update({
            'name': k,
            'type': 'bool',
            'value': False,
            'expanded': False
        }
        )

        if k != 'output':
            v.update({
                'removable': True,
                'context': {'before': 'Move before',
                            'after': 'Move after'}
            })

        if k == 'output':
            v.update({'title': f"Final output{' ' * 10}"})

        procs[key][k] = v

    return procs[key]


# ----------------------------------------------------------------------------------------------------------------------
class RegionGroup(parameterTypes.GroupParameter):

    # ..................................................................................................................
    def __init__(self, **opts):

        opts['type'] = 'group'
        opts['addText'] = "Add new ..."
        super().__init__(**opts)

        scp.debug_('New region group added')
        self.sigChildAdded.connect(self.addRegion)
        self.current_index = 0

    # ..................................................................................................................
    def addRegion(self, param, child, pos):

        kind = self.parent().param('kind').value()

        if child.value() == 'undefined':
            # dimension
            dim = self.parent().parent().parent().parent().dataset.dims[-1]
            # default span
            rangex = np.array(self.parent().parent().parent().parent().parent.plotwidget.p.getAxis('bottom').range)
            x = rangex.mean()
            w = rangex.ptp() / 50
            span = (x - w, x + w)
        else:
            dim, span = child.value().split('> ')
            span = eval(span)

        # add it
        self.parent().regions.addRegion(child, kind=kind, span=span, dim=dim)
        scp.debug_(f'> new {kind} region added to the regions (index: {self.current_index})')

    # ..................................................................................................................
    def addNew(self, span=None):

        kind = self.parent().param('kind').value()
        if kind == 'undefined':
            info_msg(self.parent().parent().parent().parent(), 'Warning',
                     'Warning: kind is undefined.\n\nSelecting a kind is required before trying to add a region!')
            return

        name = f"{self.parent().name().split('#')[1]}.{self.current_index}"
        title = 'Range'
        range = self.addChild(dict(name=name,
                               title=f"{title}",
                               type='str',
                               value='undefined' if span is None else span,
                               readonly=True,
                               removable=True,
                               ))

        self.current_index += 1

        return range

registerParameterType('regiongroup', RegionGroup, override=True)

# ----------------------------------------------------------------------------------------------------------------------
class ProcessGroup(parameterTypes.GroupParameter):

    # ..................................................................................................................
    def __init__(self, **opts):

        self.processors = getProcessors('processing')

        opts['type'] = 'group'
        opts['addText'] = "Add process ..."
        opts['addList'] = self.processors
        super().__init__(**opts)

        self.current_index = 0
        self._restoring = False

        self.sigStateChanged.connect(self.processgroupChanged)

    def processgroupChanged(self, group, change, info):

        if change == 'childAdded' and info[0].name().startswith('define region'):

            child = info[0]
            child.regions = Regions()
            child.param('kind').sigStateChanged.connect(child.regions.change)
            child.sigRemoved.connect(child.regions.remove)

    # ..................................................................................................................
    def addNew(self, key):

        item = self.processors[key]
        name = f"{key}#{self.current_index}"
        item['title'] = f"{key}{' '*(20 - len(key))}"
        item['name'] = name

        child = self.insertChild(len(self.childs)-1, item)
        scp.debug_(f"New processor added: {name}")
        self.current_index += 1
        return child

    # ..................................................................................................................
    def restoreState(self, state, **kwargs):

        # remove processing children but output. They will be restored latter
        state_children = OrderedDict()
        for key in list(state['children'].keys())[:]:
            item = state['children'][key]
            if key != 'output':
                state_children[key] = item
                del state['children'][key]

        super().restoreState(state, **kwargs)

        # now we can add the define region entries
        for key in state_children.keys():
            item, _ = key.split('#')
            child = self.addNew(item)
            child.setOpts(value = state_children[key]['value'])
            child.setOpts(expanded = state_children[key]['expanded'])
            if item == 'define regions':
                # set the stored kind to this new child
                child.param('kind').setValue(state_children[key]['children']['kind']['value'])
                if child.param('kind').value()  != 'undefined':
                    child.param('kind').setOpts(readonly=True)
                # now we need to add the children ranges
                try:
                    for item in state_children[key]['children']['regiongroup']['children'].values():
                        span = child.param('regiongroup').addNew(span=item['value'])
                        span.parent().setOpts(expanded = state_children[key]['children']['regiongroup']['expanded'])
                except KeyError:
                    continue

        scp.debug_('ProcessGroup restored')

# ----------------------------------------------------------------------------------------------------------------------
class Controller(ParameterTree):

    isProcessing = False
    isInitializing = False
    params = None

    _dataset = None
    _processed = None
    _params = None

    # ..................................................................................................................
    def __init__(self, parent):

        super().__init__(showHeader=False)

        self.parent = parent
        self.itemClicked.connect(self.selectRegion)
        self.itemExpanded.connect(partial(self.showRegions, True))
        self.itemCollapsed.connect(partial(self.showRegions, False))

    # ..................................................................................................................
    @property
    def dataset(self):
        return self._dataset

    @dataset.setter
    def dataset(self, dataset):
        if not self.isInitializing:
            self.parent.plotwidget.draw(dataset, False)
        self._dataset = dataset

    # ..................................................................................................................
    @property
    def processed(self):
        return self._processed

    # ..................................................................................................................
    @property
    def params(self):
        return self._params

    # ..................................................................................................................
    def onProjectChanged(self, change):

        if change in ['opened', 'renamed', 'dataset added', 'dataset removed']:
            self.parent.save_action.setDisabled(False)
            self.parent.save_as_action.setDisabled(False)
            self.parent.close_action.setDisabled(False)
            self.parent.add_dataset_action.setDisabled(False)
            self.parent.projectwidget.setProject(self.parent.project())
            if len(self.parent.project().datasets) < 1:
                self.parent.remove_dataset_action.setDisabled(True)
            else:
                self.parent.remove_dataset_action.setDisabled(False)

        if change == 'closed':
            self.parent.save_action.setDisabled(True)
            self.parent.save_as_action.setDisabled(True)
            self.parent.close_action.setDisabled(True)
            self.parent.add_dataset_action.setDisabled(True)
            self.parent.projectwidget.setProject(None)
            self.onDatasetChanged(None)

    # ..................................................................................................................
    def onDatasetChanged(self, dataset, change=None):

        if dataset is None or change == 'select':
            if hasattr(self.parent, 'plotwidget'):
                self.parent.plotwidget.close()
                del self.parent.plotwidget
                self.parent.dplot.hideTitleBar()
            self.clear()
            if change != 'select':
                return

        scp.debug_(f'Update controller: {dataset.name}')

        # Update the controller
        if change == 'select':
            self._params = None

        self.initialize(dataset)

        # Redraw
        self.parent.setupPlot(title=dataset.name)
        self.parent.plotwidget.draw(dataset, zoom_reset=True)


    def isRegion(self, item):

        # respond to region clicks - do we click on a region's param?
        if not hasattr(item, 'param'):
            return None, None
        isregion = item.param.name().startswith('define regions')
        par = item.param
        try:
            if not isregion:
                isregion = item.param.parent() is not None and item.param.parent().name().startswith('define regions')
                par = item.param.parent()
            if not isregion:
                isregion = item.param.parent().parent() is not None \
                            and item.param.parent().parent().name().startswith('define regions')
                par = item.param.parent().parent()
        except AttributeError:
            pass

        return isregion, par

    # ..................................................................................................................
    def showRegions(self, visibility, item):

        isregion, par = self.isRegion(item)
        if isregion:
            par.opts['expanded'] = visibility
            if not self.isInitializing:
                try:
                    self.parent.plotwidget.draw_regions()
                except Exception as e:
                    scp.error_(e)

    def selectRegion(self, item):

        isregion, par = self.isRegion(item)
        if isregion:
            if item.param.parent().name() == 'regiongroup':
                kind = item.param.parent().parent().param('kind').value()
                name = item.param.name()
                # deselect all
                p = item.param.parent().parent()
                dim = self.dataset.dims[-1]
                for regionItem in p.regions.getLinearRegions(kind, dim).values():
                    regionItem[0].setMouseHover(False)
                regionItem = p.regions.findLinearRegion(name, kind, dim)
                regionItem[0].setMouseHover(True)

# ..................................................................................................................
    def change(self, params, changes):

        dataset = self.dataset

        if self.isProcessing or self.isInitializing or dataset is None:
            return

        state = params.saveState()

        if dataset.state != state:
            dataset.state = state
            self.parent.project.dirty = True
            # variable
        elif changes[0][1] != 'contextMenu':
            return

        for param, change, data in changes:

            if change == 'parent' and data is None:
                # when an element is removed
                self.parent.plotwidget.draw(dataset, False)
                return

            # Name of the parameter or group changed
            name = param.name()
            scp.debug_(f'{name} changed `{changes}`')

            # parents?
            top_group = param
            top_parent = param.parent()
            if top_parent is None:
                return
            while top_parent.name() != 'params':
                top_group = top_parent
                top_parent = top_parent.parent()

            # actions
            if top_group.name() == 'processing':
                scp.debug_('processing changed -> execute actions')
                self.processingChanged(dataset, params, param, change, data)

            return

    # ..................................................................................................................
    def processingChanged(self, dataset, params, param, change, data):

        name = param.name()

        if name=='processing' and change=='childAdded':
            # in principe there is no immediate change
            return

        if name=='kind' and change=='value' and data!='undefined':
            param.setOpts(readonly=True)
            return

        # if name=='output' and change=='value' and not data:
        #     return

        # processing item context menu
        if change == 'contextMenu':
            if data in ['before', 'after']: # Move up
                params.blockSignals(True)# with treeChangeBlocker():
                self.moveParameters(dataset, params, param, data)
                params.blockSignals(False)

        dataset = self.performProcessing(dataset, params)
        self.dataset = dataset
        return

    # ..................................................................................................................
    def exportScript(self):

        params = self.params
        actions = self.getProcessingActions(params)

        script = ""

        for action in actions:
            if action is None:
                continue

            cmdtxt = action[0].split('.')
            kwargs = action[1]

            if len(cmdtxt) > 1:
                # call from a library or a script to import
                lib = import_module(cmdtxt[0])
                func = cmdtxt[1]

            else:
                lib = self
                func = cmdtxt[0]

            if func == 'defineRegion':
                script += f"{kwargs['kind']}_ranges = {kwargs['range']}\n"
                continue # next actions

            args = ''
            if func == 'basc':
                args = '*baseline_ranges, '

            kw = ""
            for k,v in kwargs.items():
                if isinstance(v, str):
                    v = f"'{v}'"
                kw += f"{k}={v}, "
            if kw.endswith(", "):
                kw = kw[:-2]
            script += f"dataset.{func}({args}{kw})\n"

        if not script:
            return


    def importScript(self):
        """

        Returns
        -------

        """

    # ..................................................................................................................
    def roiChanged(self, dataset, param, change, data):
        # ROI : this can affect plotting and processing

        name = param.name()

        if name.startswith('lower') or name.startswith('upper'):
            # ROI setting
            dim = name[-1]
            index = 0 if name.startswith('lower') else 1
            coord = getattr(dataset, dim)
            roi = coord.roi
            roi[index] = data
            coord.roi = roi

        elif name == 'setrefy':
            self.setrefy = True
            refy = p.param('ROI').param('yROI').param('refy')
            refy.setValue(p.param('ROI').param('yROI').param('lowery').value())

        elif name == 'refy':
            p.blockSignals(True) # avoid propagating new changes events
            refy = p.param('ROI').param('yROI').param('refy').value()
            par = p.param('ROI').param('yROI').param('lowery')
            par.setValue(par.value() - refy)
            par = p.param('ROI').param('yROI').param('uppery')
            par.setValue(par.value() - refy)
            dataset.y.data -= refy
            dataset.y.roi = [dataset.y.roi[0] - refy, dataset.y.roi[1] - refy]
            p.param('ROI').param('yROI').param('setrefy').hide()
            self.setrefy = False
            p.blockSignals(False)
            return

        return

    # ..................................................................................................................
    def moveParameters(self, dataset, params, param, data):

        state = params.saveState()

        proc = state['children']['processing']['children']
        children = list(proc.keys())
        index = i = children.index(param.name())
        if data == 'before' and index > 0:
            children[i - 1], children[i] = children[i], children[i - 1]
        elif data == 'after' and index < len(children) - 1:
            children[i + 1], children[i] = children[i], children[i + 1]
        new = type(proc)()
        for k in children:
            new[k] = proc[k]
        state['children']['processing']['children'] = new
        dataset.state = state
        self.initialize(dataset)

    # ..................................................................................................................
    def performProcessing(self, dataset, params):

        params.blockSignals(True)

        # Get the processing steps
        dataset.state = params.saveState()  # save current parameters
        actions = self.getProcessingActions(params)

        # Reset dataset to original
        dataset.processeddata = None
        dataset.processedmask = False

        transposed = dataset.transposed
        if transposed:
            dataset.transpose(inplace=True)

        # execute all actions
        if actions:
            self.isProcessing = True
            dataset = self.propagateActions(dataset, actions)
            self.isProcessing = False

        if dataset.transposed != transposed:
            if hasattr(self.parent, 'plotwidget'):
                self.parent.plotwidget.sigZoomReset.emit()

        params.blockSignals(False)
        return dataset

    # ..................................................................................................................
    def getProcessingActions(self, params):

        # Brute force method: if any of the processing parameters change, we reevaluate all processing step (will
        # be refined later)

        proc = params.param('processing')
        actions = []

        for item in proc:
            if not item.value():
                # item not checked, we do not take it into account
                continue

            actions.append([item.opts['action']])

            parameters = {}
            if not item.name().startswith('define regions'):
                if item.childs:
                    for children in item.childs:
                        parameters[children.name()] = children.value()
            else:
                parameters['kind'] = item.param('kind').value()
                parameters['range'] = [list(eval(val.value().split('> ')[1]))
                                       for val in item.param('regiongroup').children()]

            actions[-1].append(parameters)

        scp.debug_('ACTIONS: ')
        scp.debug_(actions)

        return actions

    # ..................................................................................................................
    def propagateActions(self, dataset, actions):
        if actions is None or actions == [None]:
            # Only output, but set to None
            return

        # input
        new = dataset.copy()

        # apply actions
        nprocess = 0
        for action in actions:
            if action is None:
                continue

            nprocess += 1
            scp.debug_(f'Action running: {action}')
            cmdtxt = action[0].split('.')

            if len(cmdtxt) > 1:
                # call from a library or a script to import
                lib = import_module(cmdtxt[0])
                f = cmdtxt[1]
            else:
                lib = self
                f = cmdtxt[0]
            func = getattr(lib, f)
            kwargs = action[1]
            new = func(new, **kwargs)

        if nprocess and new is not None:
            dataset.processeddata = new.data
            dataset.processedmask = new.mask
            if new.transposed:
                # in this case the original data must also be transposed
                dataset.transpose(inplace=True)
        else:
            dataset.processeddata = None
            dataset.processedmask = False

        return dataset

    # ..................................................................................................................
    def processingOutput(self, dataset, name):
        """
        When this action is executed, a new dataset must be added with the processed data in the current
        dataset subproject

        """
        supname = dataset.name.split('/')[0]

        new = dataset.copy()  # we do not want to modify the current dataset when writing in a new dataset
        new.name = f'{supname}/{name}'

        # We do not want to propagate the current processing children (except the default output)

        for key in list(new.state['children']['processing']['children'].keys())[:]:
            if key.strip() != 'output':
                del new.state['children']['processing']['children'][key]
            else:
                new.state['children']['processing']['children'][key]['children']['name']['value'] = 'untitled'
                new.state['children']['processing']['children'][key]['value'] = False

        new.data = new.processeddata
        new.mask = new.processedmask
        new.processeddata = None
        new.processedmask = False

        self.parent.project.updateDataset(new)

        return dataset

    def processingROI(self):
        # TODO
        self.setrefy = False

        lowerx = {'name':   'lowerx', 'title': 'Lower x limit', 'type': 'float', 'limits': dataset.x.limits,
                  'tip':    'Lower x limit of the ROI', 'value': dataset.x.roi[0], 'decimals': 1,
                  'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'}

        upperx = {'name':   'upperx', 'title': 'Upper x limit', 'type': 'float', 'limits': dataset.x.limits,
                  'tip':    'Upper limit of the ROI', 'value': dataset.x.roi[1], 'decimals': 1,
                  'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'}

        xtitle = f"{dataset.x.title} / {dataset.x.units:~P}"
        dicroi1d = {  # Group ROI
            'name': 'xROI', 'title': xtitle, 'type': 'group', 'children': [lowerx, upperx]}

        lowery = {'name':   'lowery', 'title': 'Lower series limit', 'type': 'float',
                  'tip':    'Lower limit of the series', 'value': dataset.y.roi[0], 'decimals': 1,
                  'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'}

        uppery = {'name':   'uppery', 'title': 'Upper series limit', 'type': 'float',
                  'tip':    'Upper limit of the series', 'value': dataset.y.roi[1], 'decimals': 1,
                  'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'}

        ytitle = f"{dataset.y.title} / {dataset.y.units:~P}"
        dicroi2d = {  # Group ROI
            'name': 'yROI', 'title': ytitle, 'type': 'group', 'children': [lowery, uppery]}

        if 'GMT' in dataset.y.title:
            refy = {'name':  'refy', 'title': 'GMT Reference', 'type': 'float', 'tip': 'Reference time for GMT series',
                    'value': 0, 'decimals': 1, 'format': '{scaledValue:.{decimals}f}{suffixGap}{siPrefix}{suffix}'}

            setrefy = {'name': 'setrefy', 'title': 'Set relative time', 'type': 'action'}

            dicroi2d['children'].extend([refy, setrefy])

        roi = {  # ROI group
            'name':     'ROI', 'title': 'Region of interest (ROI)', 'type': 'group', 'expanded': False,
            'children': [dicroi1d] if ndim < 2 else [dicroi1d, dicroi2d]}

        params = [roi]

    # ------------------------------------------------------------------------------------------------------------------
    # Regions
    # ------------------------------------------------------------------------------------------------------------------

    # ..................................................................................................................
    def defineRegion(self, dataset, **kwargs):

        kind = kwargs.get('kind', 'undefined')
        ranges = kwargs.get('range', None)

        if kind == 'mask':
            return self.setMask(dataset, ranges)

        else:
            return self.setRegion(dataset, kind, ranges)

    # ..................................................................................................................
    def setMask(self, dataset, ranges):

        for span in ranges:
            low, up = span
            dataset[:, low:up] = scp.MASKED
        return dataset

    # ..................................................................................................................
    def setRegion(self, dataset, kind, ranges):

        if 'regions' not in dataset.meta:
            dataset.meta['regions'] = {'baseline': [], 'integral': [], 'undefined': []}
        dataset.meta.regions[kind] = ranges

        return dataset


    # ------------------------------------------------------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------------------------------------------------------

    def _renameChild(self, params, name):

        # for further actions if necessary
        return name

    # ..................................................................................................................
    def initialize(self, dataset):

        if dataset is None:
            self._dataset = None
            self._params = None
            return

        scp.debug_('initialize controller')
        self.isInitializing = True
        params = self.params

        if params is None or not dataset.state:
            ndim = dataset._squeeze_ndim
            processing = ProcessGroup(
                    name='processing',
                    title='Processing pipeline',
                    children=[
                        getProcessors('basis')['output']
                    ]
            )
            params = [processing]

            scp.debug_('create group')

            # Create tree of Parameter objects
            params = Parameter.create(name='params', type='group', children=params)
            params._parent = self
            self.setParameters(params, showTop=False)

        if dataset.state:
            scp.debug_('Restore state')
            # was already saved before. Restore it
            params.restoreState(dataset.state, blockSignals=True)

        # actualise
        scp.debug_('Save state')
        dataset.state = params.saveState()
        dataset = self.performProcessing(dataset, params)
        for item in params.param('processing'):
            item.opts['expanded'] = False
        self._params = params

        # set the current dataset
        self._dataset = dataset

        # connects events
        self._params.sigTreeStateChanged.connect(self.change)

        self.isInitializing = False
        scp.debug_('Initialisation finished')
