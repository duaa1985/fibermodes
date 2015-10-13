from PySide import QtGui, QtCore
import pyqtgraph as pg
from fibermodesgui import blockSignals
from fibermodes import ModeFamily


FIBERS, WAVELENGTHS, VNUMBER, MODES = range(4)
YAXISLIST = QtCore.Qt.UserRole + 1
MARK = ["None", "Mode", 'o', 's', 't', 'd', '+']
MARKM = {ModeFamily.HE: 'o', ModeFamily.EH: 's', ModeFamily.TE: 't',
         ModeFamily.TM: 'd', ModeFamily.LP: '+'}


class PlotOptions(QtGui.QDialog):

    def __init__(self, parent, f=0):
        super().__init__(parent, f)
        self.parent = parent

        self.showLegend = QtGui.QCheckBox(self.tr("Show legend"))
        self.showLegend.stateChanged.connect(parent.updatePlot)

        self.showCutoffs = QtGui.QCheckBox(self.tr("Show cutoffs"))
        self.showCutoffs.stateChanged.connect(parent.updatePlot)
        self.showCutoffs.setEnabled(False)

        self.showLayers = QtGui.QCheckBox(self.tr("Show layer boundaries"))
        self.showLayers.stateChanged.connect(parent.updatePlot)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.showLegend)
        layout.addWidget(self.showCutoffs)
        layout.addWidget(self.showLayers)
        self.setLayout(layout)

    def hideEvent(self, event):
        self.parent.optionsBut.setChecked(False)
        return super().hideEvent(event)

    def save(self):
        return {
            'legend': self.showLegend.isChecked(),
            'cutoffs': self.showCutoffs.isChecked(),
            'layers': self.showLayers.isChecked()
        }

    def load(self, options):
        with blockSignals(self.showLegend):
            self.showLegend.setChecked(options['legend'])
        with blockSignals(self.showCutoffs):
            self.showCutoffs.setChecked(options['cutoffs'])
        with blockSignals(self.showLayers):
            self.showLayers.setChecked(options['layers'])
        self.parent.updatePlot()


class ColorPickerItemDelegate(QtGui.QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        color = index.data()
        new_color = QtGui.QColorDialog.getColor(
            color, parent, self.tr("Select color"))
        if new_color.isValid():
            index.model().setData(index, new_color)
        return None


class ComboBoxItemDelegate(QtGui.QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        items = index.data(role=YAXISLIST)
        if items:
            combo = QtGui.QComboBox(parent)
            combo.addItems(items)
            combo.currentIndexChanged.connect(self.currentIndexChanged)
            return combo
        return None

    def setEditorData(self, editor, index):
        with blockSignals(editor):
            editor.setCurrentIndex(index.data(QtCore.Qt.UserRole))

    def currentIndexChanged(self, index):
        self.commitData.emit(self.sender())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex())


class MarkItemDelegate(QtGui.QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        combo = QtGui.QComboBox(parent)
        combo.addItems(MARK)
        combo.currentIndexChanged.connect(self.currentIndexChanged)
        return combo

    def setEditorData(self, editor, index):
        with blockSignals(editor):
            editor.setCurrentIndex(index.data(QtCore.Qt.UserRole))

    def currentIndexChanged(self, index):
        self.commitData.emit(self.sender())

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex())


class YAxisTableView(QtGui.QTableView):

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setModel(model)
        self.comboBoxItemDelegate = ComboBoxItemDelegate(self)
        self.colorPickerItemDelegate = ColorPickerItemDelegate(self)
        self.markItemDelegate = MarkItemDelegate(self)
        self.setItemDelegateForColumn(0, self.comboBoxItemDelegate)
        self.setItemDelegateForColumn(1, self.colorPickerItemDelegate)
        self.setItemDelegateForColumn(2, self.markItemDelegate)


class PlotModel(QtCore.QAbstractTableModel):

    def __init__(self, parent):
        super().__init__(parent)
        self.doc = parent.doc

        self.plots = [[0, QtGui.QColor("red").rgba(), 0]]
        self.usecolor = [False]

    def rowCount(self, parent=QtCore.QModelIndex):
        return len(self.plots)

    def columnCount(self, parent=QtCore.QModelIndex):
        return 3

    def data(self, index, role=QtCore.Qt.DisplayRole):
        value = self.plots[index.row()][index.column()]

        if index.column() == 0:
            if role == YAXISLIST:
                return self.doc.params
            if role == QtCore.Qt.UserRole:
                return value

            if role == QtCore.Qt.DisplayRole:
                try:
                    return self.doc.params[value]
                except IndexError:
                    return ''

        elif index.column() == 1:  # color
            value = QtGui.QColor.fromRgba(value)

            if role == QtCore.Qt.CheckStateRole:
                return (QtCore.Qt.Checked if self.usecolor[index.row()]
                        else QtCore.Qt.Unchecked)

            if role == QtCore.Qt.DisplayRole:
                return (value if self.usecolor[index.row()]
                        else self.tr("Automatic"))

            if not self.usecolor[index.row()]:
                return None

            if role == QtCore.Qt.BackgroundRole:
                return value

            if role == QtCore.Qt.TextColorRole:
                r = value.redF()
                r = r/12.92 if r <= 0.03928 else ((r+0.055)/1.055)**2.4
                g = value.greenF()
                g = g/12.92 if g <= 0.03928 else ((g+0.055)/1.055)**2.4
                b = value.blueF()
                b = b/12.92 if b <= 0.03928 else ((b+0.055)/1.055)**2.4
                L = 0.2126 * r + 0.7152 * g + 0.0722 * b
                if L > 0.179:
                    return QtGui.QColor('black')
                else:
                    return QtGui.QColor('white')

        elif index.column() == 2:  # mark
            if role == QtCore.Qt.UserRole:
                return value
            elif role == QtCore.Qt.DisplayRole:
                return MARK[value]

        if role == QtCore.Qt.DisplayRole:
            return value

    def setData(self, index, value, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.CheckStateRole:
            self.usecolor[index.row()] = (value == QtCore.Qt.Checked)
        else:
            if index.column() == 1:
                value = value.rgba()
            self.plots[index.row()][index.column()] = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        if index.column() == 1:
            return (QtCore.Qt.ItemIsEditable |
                    QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsUserCheckable)
        else:
            return (QtCore.Qt.ItemIsEditable |
                    QtCore.Qt.ItemIsEnabled)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                labels = [self.tr("y axis"),
                          self.tr("Color"),
                          self.tr("Mark")]
                return labels[section]
            else:
                return str(section + 1)

    def save(self):
        return {
            'plots': self.plots,
            'usecolor': self.usecolor
        }

    def load(self, data):
        self.plots = data['plots']
        self.usecolor = data['usecolor']
        self.layoutChanged.emit()


class PlotFrame(QtGui.QFrame):

    modified = QtCore.Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.doc = parent.doc
        self._wl = self._fnum = 0
        self._modesel = []

        self.plotOptions = PlotOptions(self)

        self.plot = pg.PlotWidget()
        self.legend = None
        self.plotModel = PlotModel(self)
        self.yAxisTable = YAxisTableView(self.plotModel)
        self.plotModel.dataChanged.connect(self.updatePlot)

        layout = QtGui.QVBoxLayout()
        layout.addLayout(self._xAxisLayout())
        layout.addWidget(self.yAxisTable)
        layout.addWidget(self.plot, stretch=1)
        self.setLayout(layout)

    def _xAxisLayout(self):
        self.xAxisSelector = QtGui.QComboBox()
        self.xAxisSelector.addItem(self.tr("Fibers"))
        self.xAxisSelector.addItem(self.tr("Wavelengths"))
        self.xAxisSelector.addItem(self.tr("V number"))
        # self.xAxisSelector.addItem(self.tr("Modes"))
        self.xAxisSelector.currentIndexChanged.connect(self.updatePlot)
        self.xAxisSelector.setCurrentIndex(VNUMBER)

        self.optionsBut = QtGui.QPushButton(
            QtGui.QIcon.fromTheme('document-properties'),
            self.tr("Options"))
        self.optionsBut.setCheckable(True)
        self.optionsBut.toggled.connect(self.plotOptions.setVisible)

        layout = QtGui.QHBoxLayout()
        layout.addWidget(QtGui.QLabel(self.tr("x axis:")))
        layout.addWidget(self.xAxisSelector)
        layout.addWidget(self.optionsBut)
        layout.addStretch(1)
        return layout

    def setFiber(self, value):
        self._fnum = value - 1
        self.updatePlot()

    def setWavelength(self, value):
        self._wl = value - 1
        self.updatePlot()

    def updateModeSel(self, modes):
        self._modesel = modes
        self.updatePlot()

    def updatePlot(self):
        if not self.doc.initialized:
            return

        self.plot.clear()
        if self.plotOptions.showLegend.isChecked():
            if self.legend is not None:
                self.legend.scene().removeItem(self.legend)
            self.legend = self.plot.addLegend()
        elif self.legend is not None:
            self.legend.scene().removeItem(self.legend)
            self.legend = None

        self._updateXAxis()

        self.miny = float("inf")
        self.maxy = -float("inf")
        for i in range(self.plotModel.rowCount()):
            self.plotGraph(i)
        try:
            viewBox = self.plot.getPlotItem().getViewBox()
            viewBox.setYRange(self.miny, self.maxy)
        except:
            pass

        if (self.plotOptions.showCutoffs.isEnabled() and
                self.plotOptions.showCutoffs.isChecked()):
            self.plotCutoffs()

        if self.plotOptions.showLayers.isChecked():
            self.plotLayers()

    def _updateXAxis(self):
        index = self.xAxisSelector.currentIndex()

        if index == FIBERS:
            self.X = range(1, len(self.doc.fibers)+1)
        elif index == WAVELENGTHS:
            self.X = self.doc.wavelengths
        elif index == VNUMBER:
            fiber = self.doc.fibers[self._fnum]
            self.X = [fiber.V0(w) for w in self.doc.wavelengths[::-1]]
        # elif index == MODES:
        #     self.X = list(self.doc._simulator.modes(self._fnum, self._wl))

        units = 'm' if index == WAVELENGTHS else ''
        self.plot.getPlotItem().setLabel('bottom',
                                         self.xAxisSelector.currentText(),
                                         units)

        if index == WAVELENGTHS and "cutoff (wavelength)" in self.doc.params:
            self.plotOptions.showCutoffs.setEnabled(True)
        elif index == VNUMBER and "cutoff (V)" in self.doc.params:
            self.plotOptions.showCutoffs.setEnabled(True)
        else:
            self.plotOptions.showCutoffs.setEnabled(False)

        viewBox = self.plot.getPlotItem().getViewBox()
        viewBox.setXRange(self.X[0], self.X[-1])
        self.modified.emit()

    def plotGraph(self, row):
        what = self.plotModel.data(self.plotModel.index(row, 0),
                                   QtCore.Qt.UserRole)
        color = self.plotModel.data(self.plotModel.index(row, 1),
                                    role=QtCore.Qt.BackgroundRole)
        mark = self.plotModel.data(self.plotModel.index(row, 2))
        if mark == 'None':
            mark = None if len(self.X) > 1 else 'o'
        xaxis = self.xAxisSelector.currentIndex()

        y = {}
        if xaxis == FIBERS:
            for (f, w, m, j), v in self.doc.values.items():
                if j == what and w == self._wl:
                    if m in y:
                        y[m].append((f+1, v))
                    else:
                        y[m] = [(f+1, v)]
        else:
            for (f, w, m, j), v in self.doc.values.items():
                if j == what and f == self._fnum:
                    if m in y:
                        y[m].append((w, v))
                    else:
                        y[m] = [(w, v)]

        for m, xy in y.items():
            X, Y = zip(*sorted(xy))
            if xaxis == VNUMBER:
                X = [self.X[-x-1] for x in X]
            elif xaxis == WAVELENGTHS:
                X = [self.X[x] for x in X]

            col = color if color else m.color()
            symb = MARKM[m.family] if mark == 'Mode' else mark
            symbb = col if mark else None
            pen = pg.mkPen(color=col, width=3 if m in self._modesel else 1)
            spen = pg.mkPen(color='w', width=2 if m in self._modesel else 1)
            self.plot.plot(X, Y, pen=pen, symbol=symb,
                           symbolBrush=symbb, symbolPen=spen, name=str(m))
            miny = min(Y)
            maxy = max(Y)
            self.miny = min(miny, self.miny)
            self.maxy = max(maxy, self.maxy)

    def plotCutoffs(self):
        xaxis = self.xAxisSelector.currentIndex()
        if xaxis == WAVELENGTHS:
            index = self.doc.params.index("cutoff (wavelength)")
        else:
            index = self.doc.params.index("cutoff (V)")
        for (f, w, m, j), v in self.doc.values.items():
            if j == index and f == self._fnum and w == 0:
                if self.X[0] < v < self.X[-1]:
                    color = self.plotModel.data(self.plotModel.index(j, 1),
                                                role=QtCore.Qt.BackgroundRole)
                    col = color if color else m.color()
                    self.plot.addLine(
                        x=v,
                        pen=pg.mkPen(color=col,
                                     style=QtCore.Qt.DashLine,
                                     width=3 if m in self._modesel else 1))

    def plotLayers(self):
        if self.plotModel.rowCount() == 0:
            return
        what = self.plotModel.data(self.plotModel.index(0, 0),
                                   QtCore.Qt.UserRole)
        p = self.doc.params[what]
        norm = True if p == 'b' else False

        xaxis = self.xAxisSelector.currentIndex()
        if xaxis == FIBERS:
            wl = self.doc.wavelengths[self._wl]
            if norm:
                n1 = [max(layer.maxIndex(wl) for layer in fiber.layers)
                      for fiber in self.doc.fibers]
                n2 = [fiber.maxIndex(-1, wl) for fiber in self.doc.fibers]
            for i in range(len(self.doc.fibers[0])):  # TODO: merged layers...
                n = [fiber.maxIndex(i, wl) for fiber in self.doc.fibers]
                if norm:
                    for i in range(len(n)):
                        n[i] = (n[i]**2 - n2[i]**2) / (n1[i]**2 - n2[i]**2)
                self.plot.plot(self.X, n,
                               pen=pg.mkPen(color='w',
                                            style=QtCore.Qt.DotLine))
        else:
            fiber = self.doc.fibers[self._fnum]
            wls = (self.doc.wavelengths if xaxis == WAVELENGTHS
                   else self.doc.wavelengths[::-1])
            if norm:
                n1 = [max(layer.maxIndex(wl) for layer in fiber.layers)
                      for wl in wls]
                n2 = [fiber.maxIndex(-1, wl) for wl in wls]
            for layer in fiber.layers:
                n = [layer.maxIndex(wl) for wl in wls]
                if norm:
                    for i in range(len(n)):
                        n[i] = (n[i]**2 - n2[i]**2) / (n1[i]**2 - n2[i]**2)
                self.plot.plot(self.X, n,
                               pen=pg.mkPen(color='w',
                                            style=QtCore.Qt.DotLine))

    def save(self):
        return {
            'xaxis': self.xAxisSelector.currentIndex(),
            'options': self.plotOptions.save(),
            'yaxis': self.plotModel.save()
        }

    def load(self, options):
        self.xAxisSelector.setCurrentIndex(int(options['xaxis']))
        self.plotOptions.load(options['options'])
        self.plotModel.load(options['yaxis'])
