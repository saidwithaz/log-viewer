from sys import argv, exit
from os import environ
from re import search

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QTabWidget,
    QListWidget,
    QScrollArea,
    QLabel,
    QFrame,
    QVBoxLayout
)
from PySide2 import QtCharts

environ['QT_MAC_WANTS_LAYER'] = '1'  # This is a fix for running on macOS Monterey


def parse_log(filename):
    log_file = open(filename, "r")
    memory_sizes = []
    warnings = []
    sections = []
    section_head = ""
    section = ""
    section_line_no = 0
    total_time = ""

    for line in log_file:
        elapsed_time_regex = search(r'^Elapsed:\s*(\d+:\d+:\d+\.\d+)$', line)
        memory_regex = search(r'(\d+)MB', line)
        warning_regex = search(r'warning(:|\s+\|)', line.lower())
        error_regex = search(r'error(:|\s+\|)', line.lower())

        if warning_regex or error_regex:
            warnings.append(line)
        if ("========" in line) or ("--------" in line):
            if section != "":
                sections.append((section_head, section))
            section = ""
            section_line_no = 0
        else:
            if section_line_no == 0:
                section_head = line
            else:
                section += line.partition('|')[2]
            section_line_no += 1
        if elapsed_time_regex:
            total_time = elapsed_time_regex.group(1)
        if memory_regex:
            memory_sizes.append(int(memory_regex.group(1)))
    summary = (total_time, memory_sizes)

    return summary, warnings, sections


# This is the main window, with three tabs for Summary, Warnings + Errors, and Subsections.
class TabDialog(QDialog):

    def __init__(self, data, parent: QWidget = None):
        super().__init__(parent)
        self.setMinimumSize(800, 480)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.North)
        tabs.setMovable(True)

        tabs.addTab(Summary(data[0]), "Summary")
        tabs.addTab(WarningError(data[1]), "Warnings + Errors")
        tabs.addTab(Sections(data[2]), "Subsections")

        main_layout = QVBoxLayout()
        main_layout.addWidget(tabs)
        self.setLayout(main_layout)
        self.setWindowTitle("Log Report")

# Summary displays a chart of memory usage throughout the log file, alongside min and max usage.
class Summary(QWidget):

    def __init__(self, summary):
        super(Summary, self).__init__()

        elapsed_time_label = QLabel("Total Render Time:")
        elapsed_time_label_value_label = QLabel(summary[0])
        elapsed_time_label_value_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        max_mem_label = QLabel("Maximum Memory Used:")
        max_mem_value_label = QLabel(str(max(summary[1])) + "MB")
        max_mem_value_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        min_mem_label = QLabel("Minimum Memory Used:")
        min_mem_value_label = QLabel(str(min(summary[1])) + "MB")
        min_mem_value_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        time_mem_label = QLabel("Memory Over Time:")

        self.series = QtCharts.QtCharts.QLineSeries()
        for i in range(len(summary[1])):
            self.series.append(i, summary[1][i])
        self.chart = QtCharts.QtCharts.QChart()
        self.chart.legend().hide()
        self.chart.addSeries(self.series)

        self._axis_x = QtCharts.QtCharts.QValueAxis()
        self._axis_x.setTitleText("n")
        self._axis_x.setLabelFormat("%d")
        self._axis_x.setTickCount(10)
        self.chart.addAxis(self._axis_x, Qt.AlignBottom)
        self.series.attachAxis(self._axis_x)
        self._axis_y = QtCharts.QtCharts.QLogValueAxis()
        self._axis_y.setTitleText("Memory (MB)")
        self._axis_y.setLabelFormat("%d")
        self.chart.addAxis(self._axis_y, Qt.AlignLeft)
        self.series.attachAxis(self._axis_y)

        self._chart_view = QtCharts.QtCharts.QChartView(self.chart)
        self._chart_view.setFixedSize(800, 300)

        main_layout = QVBoxLayout()
        main_layout.addWidget(elapsed_time_label)
        main_layout.addWidget(elapsed_time_label_value_label)
        main_layout.addWidget(max_mem_label)
        main_layout.addWidget(max_mem_value_label)
        main_layout.addWidget(min_mem_label)
        main_layout.addWidget(min_mem_value_label)
        main_layout.addWidget(time_mem_label)
        main_layout.addWidget(self._chart_view)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

# This displays a simple list of collected warning/error messges
class WarningError(QWidget):

    def __init__(self, warnings):
        super(WarningError, self).__init__()

        list_widget = QListWidget()
        list_widget.setMinimumSize(800, 400)

        warnings_count = 0
        errors_count = 0
        for i in range(len(warnings)):
            list_widget.addItem(warnings[i])
            if "warning" in warnings[i].lower():
                warnings_count += 1
            else:
                errors_count += 1

        warning_label = QLabel("Total No. of Warnings:")
        warning_no_label = QLabel(str(warnings_count))
        warning_no_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        error_label = QLabel("Total No. of Errors:")
        error_no_label = QLabel(str(errors_count))
        error_no_label.setFrameStyle(QFrame.Panel | QFrame.Sunken)

        main_layout = QVBoxLayout()
        main_layout.addWidget(warning_label)
        main_layout.addWidget(warning_no_label)
        main_layout.addWidget(error_label)
        main_layout.addWidget(error_no_label)
        main_layout.addWidget(list_widget)
        main_layout.addStretch(1)
        self.setLayout(main_layout)

# This displays the sections each in their own box, all inside a scrollable area.
class Sections(QScrollArea):

    def __init__(self, sections):
        super(Sections, self).__init__()
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        for item in sections:
            main_layout.addWidget(QLabel(item[0]))
            subsection = QLabel(item[1])
            subsection.setFrameStyle(QFrame.Panel | QFrame.Sunken)
            main_layout.addWidget(subsection)

        self.setWidget(widget)


if __name__ == "__main__":
    app = QApplication(argv)

    if len(argv) == 1:
        log_file_name = input("Please specify log file name: ")
        log_data = parse_log(log_file_name)
    elif len(argv) == 2:
        log_data = parse_log(argv[1])
    else:
        exit("ERROR: Too many arguments to run program. Please only run with one log file.")

    dialog = TabDialog(log_data)
    dialog.show()

    exit(app.exec_())
