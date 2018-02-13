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
    global ACTIVE_UML_PROCESSORS
    global ACTIVE_VIEWER

    ACTIVE_UML_PROCESSORS = []
    ACTIVE_VIEWER = None

    sublime_settings = load_settings("PlantUmlDiagrams.sublime-settings")
    print("Viewer Setting: " + sublime_settings.get("viewer"))

    for plantuml_processor in AVAILABLE_PROCESSORS:
        try:
            print("Loading plantuml_processor class: %r" % plantuml_processor)
            proc = plantuml_processor()
            proc.CHARSET = sublime_settings.get('charset')
            proc.CHECK_ON_STARTUP = sublime_settings.get('check_on_startup')
            proc.NEW_FILE = sublime_settings.get('new_file')
            proc.load()
            ACTIVE_UML_PROCESSORS.append(proc)
            print("Loaded plantuml_processor: %r" % proc)
        except Exception as error:
            print("Unable to load plantuml_processor: %r, %s" % (plantuml_processor, error))
    if not ACTIVE_UML_PROCESSORS:
        raise Exception('No working processors found!')

    for viewer in AVAILABLE_VIEWERS:
        if viewer.__name__.find(sublime_settings.get("viewer")) != -1:
            try:
                print("Loading viewer class from configuration: %r" % viewer)
                vwr = viewer()
                vwr.load()
                ACTIVE_VIEWER = vwr
                print("Loaded viewer: %r" % vwr)
                break
            except Exception as error:
                print("Unable to load configured viewer, falling back to autodetection... %s" % error)

    if ACTIVE_VIEWER is None:
        for viewer in AVAILABLE_VIEWERS:
            print("Trying Viewer " + viewer.__name__)
            try:
                print("Loading viewer class: %r" % viewer)
                vwr = viewer()
                vwr.load()
                ACTIVE_VIEWER = vwr
                print("Loaded viewer: %r" % vwr)
                break
            except Exception:
                print("Unable to load viewer: %r" % viewer)
                sys.excepthook(*sys.exc_info())

    if ACTIVE_VIEWER is None:
        raise Exception('No working viewers found!')

    INITIALIZED = True
    print("Processors: %r" % ACTIVE_UML_PROCESSORS)
    print("Viewer: %r" % ACTIVE_VIEWER)


def process(view):
    diagrams = []

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
        t = Thread(target=render_and_view, args=(sourceFile, diagrams,))

        t.daemon = True
        t.start()

        return True

    else:
        return False


def render_and_view(sourceFile, diagrams):
    # print("Rendering %r" % diagrams)
    sequence = [0]
    diagram_files = []

    for plantuml_processor, text_blocks in diagrams:
        diagram_files.extend(plantuml_processor.process(sourceFile, text_blocks, sequence))
        sequence[0] += 1

    if diagram_files:
        print("%r viewing %r" % (ACTIVE_VIEWER, [d.name for d in diagram_files if d]))
        ACTIVE_VIEWER.view(diagram_files)
    else:
        error_message("No diagrams generated...")
