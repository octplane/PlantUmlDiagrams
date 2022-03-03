#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


from .base import BaseViewer
from subprocess import check_call, Popen as run_command
from sublime import platform

class PreviewViewer(BaseViewer):
    def __str__(self):
        return "OSX only viewer"

    def load(self):
        if platform() not in ("osx",):
            raise Exception("Currently only supported on MacOS")
        if not check_call("which open > /dev/null", shell=True) == 0:
            raise Exception("Can't find open")

    def view(self, diagram_files):
        displaycmd = ['open', '-a', 'Preview']
        displaycmd.extend(diagram_file.name for diagram_file in diagram_files)
        run_command(displaycmd).wait()
