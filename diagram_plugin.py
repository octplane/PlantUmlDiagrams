
import os
import time

import sublime
import threading

from sublime_plugin import TextCommand
from sublime import error_message, version
try:
    from .diagram import setup, process
except ValueError:
    from diagram import setup, process


try:
    all_views_active

except NameError:
    all_views_active = {}

from debug_tools import getLogger
log = getLogger(__package__)


def process_diagram_image(view):
    log(1, "Processing diagrams in %s..." % view.file_name())

    if not process(view):
        error_message("No diagrams overlap selections.\n\n" \
            "Nothing to process.")


class DiagramContinueCreationThread(threading.Thread):

    def __init__(self, view):
        all_views_active[view.id()] = self
        threading.Thread.__init__(self)

        # Force it to be refreshed on the first time
        self.change_count = -1

        self.view = view
        self.open_image = True
        self.sleepEvent = threading.Event()

    def run(self):
        view = self.view
        window = view.window()
        current_time = time.time()

        elapsed_time = 0.1
        mininum_time = 1.0
        default_time = 1.0

        while True:
            # log(1, "current_time: %s, elapsed_time: %s" % (current_time, elapsed_time))

            # Run until it closes
            if view not in window.views():
                log(1, "Exiting continuous thread...")
                del all_views_active[view.id()]
                return

            elif self.change_count != view.change_count() \
                    and window == sublime.active_window() \
                    and view == window.active_view():

                current_time = time.time()
                self.change_count = view.change_count()

                open_image = self.open_image
                # active_sheet = window.active_sheet()
                # group, view_index = window.get_view_index(view)

                if not process(view, self):
                    error_message("No diagrams overlap selections.\n\n" \
                        "Nothing to process.")

                # Allowed the image view to be focused on the first time it is opened
                if not open_image:
                    window.focus_view( view )
                    # window.focus_group( group )
                    # window.focus_sheet( active_sheet )

                elapsed_time = time.time() - current_time

            self.sleepEvent.wait( elapsed_time*3 if elapsed_time > mininum_time else default_time )


class DisplayDiagramsContinually(TextCommand):

    def run(self, edit):
        view = self.view
        log(1, "Processing diagrams in %s..." % self.view)

        # Force the view to the reprocessed as it associated image could have been closed
        if view.id() in all_views_active:
            continuous_processor = all_views_active[view.id()]
            continuous_processor.open_image = True
            continuous_processor.change_count = -1

        else:
            continuous_thread = DiagramContinueCreationThread( view )
            continuous_thread.start()


class DisplayDiagrams(TextCommand):
    def run(self, edit):
        process_diagram_image(self.view)

    def isEnabled(self):
        return True


if version()[0] == '2':
    setup()
else:
    def plugin_loaded():
        """Sublime Text 3 callback to do after-loading initialization"""
        try:
            setup()
        except Exception:
            error_message("Unable to load diagram plugin, check console "
                "for details.")
            raise
