"""____________________________________________________

FILENAME: setup.py
AUTHOR: Guerric PANIS
_______________________________________________________

NXP CONFIDENTIAL
Unpublished Copyright (c) 2020 NXP, All Rights Reserved.
_______________________________________________________"""

import os
import sys
from cx_Freeze import setup, Executable
import CONST as const

#setup_path = os.path.join((os.environ['USERPROFILE']), 'Documents') + '\\' + const.FOLDER_NAME + const.SETUP_PATH

bdist_msi_options = {
    'add_to_path': False,
    'all_users': True,
    #'initial_target_dir': r'[ProgramFilesFolder]\%s\%s' % (const.program_name, const.complete_name),
    'initial_target_dir': r'c:\%s\%s' % (const.program_name, const.complete_name),
    'install_icon': 'img\\app.ico',
    'target_name': 'installer_%s' % const.complete_name
    }

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    'packages': ['os', 'wx', 'numpy', 'serial', 'time', 'threading', 'pyvisa', 'openpyxl', 'can', 'subprocess'],
    'include_files': ['img\\', 'SCRIPTS\\', 'SETUPS\\', 'DOCS\\', 'CONTEXT\\', 'ControlCAN.dll'],
    'excludes': []
    }

# GUI applications require a different base on Windows (the default is for a console application).
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

# setup(name=const.program_name,
#       version=const.version,
#       description='S32K GUI for EMC',
#       options={
#           'bdist_msi': bdist_msi_options,
#           'build_exe': build_exe_options},
#       executables=[Executable('EMC_APP.py', base=base, shortcutName=const.complete_name, shortcutDir="DesktopFolder", icon='img\\app.ico')]) # targetName=complete_name + '.exe'


setup(name=const.program_name,
      version=const.version,
      description='S32K GUI for EMC',
      options={
          'bdist_msi': bdist_msi_options,
          'build_exe': build_exe_options},
      executables=[Executable('EMC_APP.py', base=base, shortcut_name=const.complete_name, shortcut_dir="DesktopFolder", icon='img\\app.ico')]) # targetName=complete_name + '.exe'
