#!/usr/bin/env python3

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QSpinBox,
                             QGridLayout, QWidget, QComboBox, QLabel, QGroupBox,
                             QSlider, QHBoxLayout)
from PyQt5.QtCore import *
import evdev
from evdev import ecodes, InputDevice, ff
import time

app = QApplication([])

DEVICE_PATH_ROLE = Qt.UserRole + 1

class DeviceProvider(QAbstractListModel):
    def __init__(self):
        super().__init__()
        self.devices = []
        self.refresh()

    def rowCount(self, parent):
        return len(self.devices)

    def data(self, index, role):
        if index.row() >= len(self.devices):
            return None

        if (role == DEVICE_PATH_ROLE):
            return self.devices[index.row()][1]
        else:
            return self.devices[index.row()][0]

    def refresh(self):
        self.devices = []
        for name in evdev.list_devices():
            dev = InputDevice(name)
            if ecodes.EV_FF in dev.capabilities():
                self.devices += [(dev.name, name)]


class ShapeSelector(QComboBox):
    def __init__(self):
        super().__init__()
        self.addItem("Square")
        self.addItem("Triangle")
        self.addItem("Sine")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.gain = 0xffff
        self.shape = ecodes.FF_SQUARE
        self.period_ms = 10
        self.magnitude = 0x7fff
        self.offset = 0
        self.phase = 0
        self.duration_ms = 1000
        self.repeat_count = 1
        self.envelope_attack_length = 0
        self.envelope_attack_level = 0
        self.envelope_fade_length = 0
        self.envelope_fade_level = 0
        self.id = None

        widget = QWidget(parent=self)
        self.setCentralWidget(widget)

        self.device_selector = QComboBox(parent=widget)
        self.device_selector.setModel(DeviceProvider())

        refresh_button = QPushButton('Refresh', parent=widget)
        refresh_button.clicked.connect(lambda: self.device_selector.model().refresh())

        play_button = QPushButton('Play', parent=widget)
        play_button.clicked.connect(self.play_clicked)
        stop_button = QPushButton('Stop', parent=widget)
        stop_button.clicked.connect(self.stop_clicked)

        layout = QGridLayout()

        layout.addWidget(QLabel("Device:"), 0, 0)
        layout.addWidget(self.device_selector, 0, 1)
        layout.addWidget(refresh_button, 0, 2)

        self.add_form(layout, 1, "Gain", 0, 100, 100, self.update_gain)

        effect_widget = QGroupBox("Effect")
        effect_layout = QGridLayout()
        effect_widget.setLayout(effect_layout)
        layout.addWidget(effect_widget, 2, 0, 1, -1)

        effect_layout.addWidget(QLabel("Shape:"), 0, 0)
        shape_selector = ShapeSelector()
        shape_selector.currentIndexChanged.connect(self.update_shape)
        effect_layout.addWidget(shape_selector, 0, 1)

        self.add_form(effect_layout, 1, "Period (ms)", 0, 0xffff, 10, self.update_period)
        self.add_form(effect_layout, 2, "Magnitude", -100, 100, 100, self.update_magnitude)
        self.add_form(effect_layout, 3, "Offset", -0x8000, 0x7fff, 0, self.update_offset)
        self.add_form(effect_layout, 4, "Phase", 0, 0xffff, 0, self.update_phase)
        self.add_form(effect_layout, 5, "Duration (ms)", 0, 0xffff, 1000, self.update_duration)
        self.add_form(effect_layout, 6, "Repeat count", 0, 0x7fffffff, 1, self.update_repeat_count)

        envelope_widget = QGroupBox("Envelope parameters")
        envelope_layout = QGridLayout()
        self.add_form(envelope_layout, 0, "Attack length (ms)", 0, 0xffff, 0, self.update_attack_length)
        self.add_form(envelope_layout, 1, "Attack level", 0, 0xffff, 0, self.update_attack_level)
        self.add_form(envelope_layout, 2, "Fade length (ms)", 0, 0xffff, 0, self.update_fade_length)
        self.add_form(envelope_layout, 3, "Fade level", 0, 0xffff, 0, self.update_fade_level)
        envelope_widget.setLayout(envelope_layout)

        effect_layout.addWidget(envelope_widget, 7, 0, 1, -1)

        w2 = QWidget()
        blayout = QHBoxLayout()
        blayout.addWidget(stop_button)
        blayout.addWidget(play_button)
        w2.setLayout(blayout)
        layout.addWidget(w2, 3, 0, 1, -1)

        layout.setRowStretch(0, 1)
        layout.setRowStretch(1, 1)
        layout.setRowStretch(2, 4)
        layout.setRowStretch(3, 0)

        widget.setLayout(layout)

    def add_form(self, layout, row, label, minimum, maximum, default_value, valueChanged_handler):
        sbox = QSpinBox()
        slider = QSlider()

        sbox.setMinimum(minimum)
        sbox.setMaximum(maximum)
        sbox.setValue(default_value)

        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(default_value)
        slider.setOrientation(Qt.Horizontal)

        slider.valueChanged.connect(lambda value: sbox.setValue(value))
        sbox.valueChanged.connect(valueChanged_handler)

        layout.addWidget(QLabel(label + ":"), row, 0)
        layout.addWidget(slider, row, 1)
        layout.addWidget(sbox, row, 2)

    def update_gain(self, value):
        self.gain = int(0xffff * value / 100)

    def update_shape(self, index):
        if index == 0:
            self.shape = ecodes.FF_SQUARE
        elif index == 1:
            self.shape = ecodes.FF_TRIANGLE
        else:
            self.shape = ecodes.FF_SINE

    def update_period(self, value):
        self.period_ms = value

    def update_magnitude(self, value):
        if value > 0:
            self.magnitude = int(0x7fff * value / 100)
        else:
            self.magnitude = int(0xffff * value / 100)

    def update_offset(self, value):
        self.offset = value

    def update_phase(self, value):
        self.phase = value

    def update_duration(self, value):
        self.duration_ms = value

    def update_repeat_count(self, value):
        self.repeat_count = value

    def update_attack_length(self, value):
        self.envelope_attack_length = value

    def update_attack_level(self, value):
        self.envelope_attack_level = value

    def update_fade_length(self, value):
        self.envelope_fade_length = value

    def update_fade_level(self, value):
        self.envelope_fade_level = value

    def play_clicked(self):
        path = self.device_selector.currentData(DEVICE_PATH_ROLE)
        if path is None:
            return

        self.device = InputDevice(path)

        # set the gain
        print("Setting gain to " + str(self.gain))
        self.device.write(ecodes.EV_FF, ecodes.FF_GAIN, self.gain)

        envelope = ff.Envelope(
                attack_length = self.envelope_attack_length,
                attack_level = self.envelope_attack_level,
                fade_length = self.envelope_fade_length,
                fade_level = self.envelope_fade_level
                )

        periodic_effect = ff.Periodic(
                waveform = self.shape,
                period = self.period_ms,
                magnitude = self.magnitude,
                offset = self.offset,
                phase = self.phase,
                envelope = envelope)

        effect = ff.Effect(
            ecodes.FF_PERIODIC, -1, 0,
            ff.Trigger(0, 0),
            ff.Replay(self.duration_ms, 0),
            ff.EffectType(ff_periodic_effect=periodic_effect)
            )

        print("playing effect: period: " + str(self.period_ms)
                + ", magnitude: " + str(self.magnitude)
                + ", offset: " + str(self.offset)
                + ", phase: " + str(self.phase)
                + ", envelope: (" + str(self.envelope_attack_length)
                            + ", " + str(self.envelope_fade_level)
                            + ", " + str(self.envelope_fade_length)
                            + ", " + str(self.envelope_fade_level)
                            + ")")
        self.id = self.device.upload_effect(effect)
        self.device.write(ecodes.EV_FF, self.id, self.repeat_count)

    def stop_clicked(self):
        self.device = None

window = MainWindow()
window.show()
app.exec_()
