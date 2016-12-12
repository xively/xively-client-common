import subprocess
import tools.xi_client_settings
from tools.xi_client_settings import XiClientPlatform
from sys import platform as _platform
import os
import string
import shutil

def get_platform_folder():
    platform_bin_folders = { ( 'linux', 'linux2' ) : 'linux', ( 'darwin' ) : 'osx' }

    for platforms, bin_folder in platform_bin_folders.items():
        if _platform in platforms:
            return bin_folder

    return ""

def generate_command_line_arguments(host, port, is_websocket=False):
    return "-h " + host + " -p " + str(port) + (" -w" if is_websocket else "")

class XiClientDriverStarter_C:

    def start_driver(self, host, port):
        commandline_start = ("../../../xively-client-c/bin/" + get_platform_folder() + "/tests/tools/xi_libxively_driver " + generate_command_line_arguments(host, port)).split()
        self._client_process = subprocess.Popen( commandline_start )

    def prepare_environment(self, ca_cert_file):

        libxively_working_directory = "libxively_cwds/" + ca_cert_file.split('.', 1)[0]

        if not os.path.isdir(libxively_working_directory):
            os.makedirs(libxively_working_directory)

        cert_path_source = "../../../xively-client-common/certs/test/" + ca_cert_file
        cert_path_target = libxively_working_directory + "/xi_RootCA_list.pem"

        if os.path.exists(cert_path_source) and not os.path.exists(cert_path_target):
            shutil.copyfile(cert_path_source, cert_path_target)


class XiClientDriverStarter_py:
    def __init__(self, python_platform, mqtt_connect_through_websocket):
        self._mqtt_connect_through_websocket = mqtt_connect_through_websocket
        xi_platform_interpreter_map = {
            XiClientPlatform.PYTHON_2 : "python",
            XiClientPlatform.PYTHON_3 : "python3"
        }
        self._py_interpreter = xi_platform_interpreter_map[python_platform]

    def start_driver(self, host, port):
        #print("*** py interpreter = " + self._py_interpreter)
        commandline_start = (self._py_interpreter + " ../tools/xi_client_driver_python.py " + generate_command_line_arguments(host, port, self._mqtt_connect_through_websocket)).split()
        self._client_process = subprocess.Popen( commandline_start )

    def prepare_environment(self, ca_cert_file):
        pass
