from __future__ import absolute_import

from .plantuml import PlantUMLProcessor
from .sublime3 import Sublime3Viewer
from .quicklook import QuickLookViewer
from .preview import PreviewViewer
from .eog import EyeOfGnomeViewer
from .freedesktop_default import FreedesktopDefaultViewer
from .windows import WindowsDefaultViewer

from threading import Thread
from sublime import error_message, load_settings

import sys


INITIALIZED = False

AVAILABLE_PROCESSORS = [PlantUMLProcessor]
AVAILABLE_VIEWERS = [
    Sublime3Viewer,
    QuickLookViewer,
    EyeOfGnomeViewer,
    PreviewViewer,
    FreedesktopDefaultViewer,
    WindowsDefaultViewer,
]

ACTIVE_UML_PROCESSORS = []
ACTIVE_VIEWER = None


def setup():
    global INITIALIZED
    sublime_settings = load_settings("PlantUmlDiagrams.sublime-settings")

    _load_viewer(sublime_settings)
    _load_preprocessor(sublime_settings)

    INITIALIZED = True
    # print("Processors: %s" % ACTIVE_UML_PROCESSORS)
    # print("Viewer: %s" % ACTIVE_VIEWER)


def _load_preprocessor(sublime_settings):
    global ACTIVE_UML_PROCESSORS
    ACTIVE_UML_PROCESSORS = []

    def load_preprocessor():

        try:
            # print("Loading plantuml_processor class: %s" % plantuml_processor)
            proc = plantuml_processor()
            proc.CHARSET = sublime_settings.get('charset', None)
            proc.CHECK_ON_STARTUP = sublime_settings.get('check_on_startup', True)
            proc.NEW_FILE = sublime_settings.get('new_file', True)
            proc.OUTPUT_FORMAT = sublime_settings.get('output_format', 'png')
            proc.load()

            ACTIVE_UML_PROCESSORS.append(proc)
            # print("Loaded plantuml_processor: %s" % proc)
            return True

        except Exception as error:
            print("Unable to load plantuml_processor: %s, %s" % (plantuml_processor, error))

        return False

    for plantuml_processor in AVAILABLE_PROCESSORS:

        if load_preprocessor():
            break

    if not ACTIVE_UML_PROCESSORS:
        print( 'PlantUMLDiagrams: ERROR, no working processors found!' )


def _load_viewer(sublime_settings):
    global ACTIVE_VIEWER
    ACTIVE_VIEWER = None

    # print("PlantUmlDiagrams Viewer Setting: " + sublime_settings.get("viewer"))

    def load_viewer(message):

        try:
            # print("Loading viewer class: %s" % viewer)
            vwr = viewer()
            vwr.load()

            global ACTIVE_VIEWER
            ACTIVE_VIEWER = vwr

            if not message:
                print("Loaded viewer: %s" % vwr)

            return True

        except Exception as error:

            if message:
                print("Unable to load configured viewer %s, falling back to autodetection... %s" % (vwr, error))

        return False

    for viewer in AVAILABLE_VIEWERS:

        if viewer.__name__.find(sublime_settings.get("viewer")) != -1:
            load_viewer(True)
            break

    if ACTIVE_VIEWER is None:

        for viewer in AVAILABLE_VIEWERS:

            if load_viewer(False):
                break

    if ACTIVE_VIEWER is None:
        raise Exception('No working viewers found!')


def process(view, continuous_processor=None):
    diagrams = []

    if continuous_processor:
        async=False

    else:
        async=True

    for plantuml_processor in ACTIVE_UML_PROCESSORS:
        text_blocks = []

        for text_block in plantuml_processor.extract_blocks(view):
            add = False

            for selection in view.sel():

                if selection.intersects(text_block):
                    add = True
                    break

            else:  # if there are no selections, add all text_blocks
                add = True

            if add:
                text_blocks.append(view.substr(text_block))

        if text_blocks:
            diagrams.append((plantuml_processor, text_blocks, ))

    if diagrams:
        sourceFile = view.file_name()

        if async:
            t = Thread(target=render_and_view, args=(sourceFile, diagrams, continuous_processor))
            t.daemon = True
            t.start()

        else:
            render_and_view(sourceFile, diagrams, continuous_processor)

        return True

    else:
        return False


def render_and_view(sourceFile, diagrams, continuous_processor):
    # print("Rendering %s" % diagrams)
    sequence = [0]
    diagram_files = []

    for plantuml_processor, text_blocks in diagrams:
        diagram_files.extend(plantuml_processor.process(sourceFile, text_blocks, sequence, continuous_processor))
        sequence[0] += 1

    if diagram_files:
        names = [d.name for d in diagram_files if d]

        if continuous_processor:

            if continuous_processor.open_image:
                print("continuous_processor: %s viewing %s" % (ACTIVE_VIEWER, names))
                ACTIVE_VIEWER.view(diagram_files)
                continuous_processor.open_image = False

        else:
            print("%s viewing %s" % (ACTIVE_VIEWER, names))
            ACTIVE_VIEWER.view(diagram_files)

    else:
        error_message("No diagrams generated...")
