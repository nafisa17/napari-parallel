# import global libraries
from typing import TYPE_CHECKING
from magicgui import magic_factory
from qtpy.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QLineEdit, QPushButton
from pyqode.python.widgets import PyCodeEdit
from dask.distributed import Client
import glob
import copy
import re
import socket

# verification of napari modules
if TYPE_CHECKING:
    import napari

# define constants
templateInput = "YYYY"
templateOutput = "XXXX"
inputSubstring = "imread("
outputSubstring = "imsave("
viewerSubstring = "viewer"
minNumLines = 15

# function to check correctness ipv4 address with tcp-port
def isValidIpv4AddressWithPort(addr, port):
    # returns True if the IPv4 address and port are valid, else False.
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((addr, port))
        sock.close()
        return True
    except socket.error:
        return False

# function to check correctness of domain name using socket library
def isValidDomain(domain):
    # returns True if the domain name is valid, else False.
    try:
        socket.gethostbyname(domain)
        return True
    except socket.gaierror:
        return False

# function to check image extension from string variable
def checkImageExtension(ext):
    # do verification
    return ext in (".jpg", ".jpeg", ".png", ".gif", ".tif")


# create class for widget of parallel calculation
class ParallelQWidget(QWidget):

    # initialization of class
    def __init__(self, napari_viewer):

        # basic initialization
        super().__init__()
        self.viewer = napari_viewer

        # create button
        buttonProcess = QPushButton("Process")
        buttonProcess.clicked.connect(self._on_click)

        # specify vertical layout for the main app
        main_layout = QVBoxLayout()

        # add button to the main layout
        main_layout.addWidget(buttonProcess)

        # field for code of image processing
        self.codeProcessing = ""

        # create a vertical layout for the scheduler section
        scheduler_layout = QVBoxLayout()

        # add text field for scheduler IP address
        labelSched = QLabel("Scheduler IP or domain address:")
        scheduler_layout.addWidget(labelSched)
        self.textFieldSched = QLineEdit()
        scheduler_layout.addWidget(self.textFieldSched)

        # add scheduler section layout to the main layout
        main_layout.addLayout(scheduler_layout)

        # create a vertical layout for the regular expression section
        regex_layout = QVBoxLayout()
        #nafisa's work
        # text field to add regular expression path to input files
        labelInputRegex = QLabel("Regular expression of path to input files:")
        regex_layout.addWidget(labelInputRegex)
        self.textFieldInputRegex = QLineEdit()
        regex_layout.addWidget(self.textFieldInputRegex)

        # text field to add path to output files
        labelOutputRegex = QLabel("Path to output files:")
        regex_layout.addWidget(labelOutputRegex)
        self.textFieldOutputRegex = QLineEdit()
        regex_layout.addWidget(self.textFieldOutputRegex)

        # specify the base name of the output files
        labelOutputName = QLabel("Base name of the output files:")
        regex_layout.addWidget(labelOutputName)
        self.textFieldOutputName = QLineEdit()
        regex_layout.addWidget(self.textFieldOutputName)

        # specify extension of the output files
        labelExtension = QLabel("Extension for output files:")
        regex_layout.addWidget(labelExtension)
        self.textFieldExtension = QLineEdit()
        regex_layout.addWidget(self.textFieldExtension)

        # add the regular expression section layout to the main layout
        main_layout.addLayout(regex_layout)

        # create a vertical layout for the message section
        message_layout = QVBoxLayout()

        # specify label for messages
        self.labelMessage = QLabel("")
        message_layout.addWidget(self.labelMessage)

        # add scheduler section layout to the main layout
        main_layout.addLayout(message_layout)

        # set the main layout for the widget
        self.setLayout(main_layout)


    # handler for "process" button
    def _on_click(self):

        # read parameters from GUI
        regExrp = self.textFieldInputRegex.text()
        pathOutput = self.textFieldOutputRegex.text()
        begStringOutput = self.textFieldOutputName.text()
        addressHost = self.textFieldSched.text()
        extensionOutput = self.textFieldExtension.text()

        # check size of code for image processing
        try:
            # define number of rows
            numRows = len(self.codeProcessing.split("\n"))
            if numRows < minNumLines:
                # change message in special label
                self.labelMessage.setText("Image workflow was not specified!")
                # return default answer
                return
        except Exception:
            # change message in special label
            self.labelMessage.setText("Image workflow was not specified!")
            # return default answer
            return

        # check correctness of regular expression
        try:
            tempResults = glob.glob(regExrp)
        except Exception:
            # change message in special label
            self.labelMessage.setText("Regular expression is not correct!")
            # return default answer
            return

        # check correct ip or domain address for dask-scheduler
        try:
            substrings = addressHost.split(":")
            if (not isValidDomain(addressHost)) and (not isValidIpv4AddressWithPort(substrings[0], int(substrings[1]))):
                # change message in special label
                self.labelMessage.setText("Ip or domain address is not correct!")
                # return default answer
                return
        except Exception:
            # change message in special label
            self.labelMessage.setText("Ip or domain address is not correct!")
            # return default answer
            return

        # check correctness of base name for output images
        try:
            pattern = r'\b\w{3,}\b'
            if not re.match(pattern, begStringOutput):
                # change message in special label
                self.labelMessage.setText("Base name for output image file is not correct!")
                # return default answer
                return
        except Exception:
            # change message in special label
            self.labelMessage.setText("Base name for output image file is not correct!")
            # return default answer
            return

        # check correctness of image extension for output images
        try:
            if not checkImageExtension(extensionOutput):
                # change message in special label
                self.labelMessage.setText("Extension for output image file is not correct!")
                # return default answer
                return
        except Exception:
            # change message in special label
            self.labelMessage.setText("Extension for output image file is not correct!")
            # return default answer
            return


        # find out all files for analysis
        allFiles = glob.glob(regExrp)

        # receive code of program
        code = self.codeProcessing
        # delete the extra rows of code
        rowsInter = code.rsplit("\n")
        i = 0
        while i < len(rowsInter):
            if viewerSubstring in rowsInter[i]:
                del rowsInter[i]
                i -= 1
            i += 1
        codeRed = "\n".join(rowsInter)

        # split code into independent rows
        rowsCode = codeRed.splitlines()
        # receive the last row
        lastRow = rowsCode[-1]
        # receive substrings using the last row
        substrings = lastRow.split(" ")
        # get name of variable using the first element of substrings
        nameVar = substrings[0]

        # determine whether code for saving is available
        saveCodeInd = False
        j = 0
        rowsInter = codeRed.rsplit("\n")
        while j < len(rowsInter):
            if outputSubstring in rowsInter[j]:
                saveCodeInd = True
                break
            j += 1

        # add new code for saving results if it is needed
        codeAdv = ""
        if (saveCodeInd == False):
            codeAdv = codeRed + "\n" + "from skimage.io import imsave" + "\n"
            codeAdv = codeAdv + "imsave(\"" + templateOutput + "\"," + nameVar + ")\n"
        else:
            codeAdv = codeRed

        # modify input part of program
        i = 0
        rowsInter = codeAdv.rsplit("\n")
        while i < len(rowsInter):
            if inputSubstring in rowsInter[i]:
                substrings = rowsInter[i].split("=")
                rowsInter[i] = substrings[0] + "= imread(\"" + templateInput + "\")"
                break
            i += 1
        codeAdv = "\n".join(rowsInter)

        # create dask-client
        client = Client(addressHost)
        # initializate variables for saving codes for image processing
        codeTasks = [None] * len(allFiles)

        # go through all files
        for i in range(len(allFiles)):
            # copy code in specific variable
            codeExec = copy.deepcopy(codeAdv)
            # modify input part of program
            j = 0
            rowsInter = codeExec.rsplit("\n")
            while j < len(rowsInter):
                if inputSubstring in rowsInter[j]:
                    substrings = rowsInter[j].split("=")
                    rowsInter[j] = substrings[0] + "= imread(\"" + allFiles[i] + "\")"
                    break
                j += 1
            codeExec = "\n".join(rowsInter)
            # modify output part of program
            j = 0
            rowsInter = codeExec.rsplit("\n")
            while j < len(rowsInter):
                if outputSubstring in rowsInter[j]:
                    substrings = rowsInter[j].split(",")
                    rowsInter[j] = "imsave(\"" + pathOutput + begStringOutput + str(i) + extensionOutput + "\"," + nameVar + ")\n"
                    break
                j += 1
            codeExec = "\n".join(rowsInter)
            # submit tasks using Dask
            codeTasks[i] = codeExec

        # submit all tasks for execution
        tasks = client.map(exec, codeTasks)
        # wait for all tasks to complete
        results = client.gather(tasks)

        # do output verification
        outputInd = True
        for result in results:
            if result != None:
                output = False
                break

        # print result of calculation
        if outputInd:
            self.labelMessage.setText("Image processing was done successfully!")
        else:
            self.labelMessage.setText("Image processing calculation has error!")


    # class method to create dask window
    @classmethod
    def get_dask_window(cls, viewer, create_editor=True, _for_testing=False):

        # initialization
        dask_window = None
        # create a new Dask window if requested
        if create_editor:
            # create window
            dask_window = ParallelQWidget(viewer)
            # add window to dock widget
            w = viewer.window.add_dock_widget(dask_window, area="left", name="Dask window")
            if not _for_testing:
                w.setFloating(True)
            # define size of window
            w.resize(700, 400)
            # return window
            return dask_window
        # default answer
        return dask_window
