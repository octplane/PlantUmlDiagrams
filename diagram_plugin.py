
import time
import sublime
import threading

from sublime_plugin import TextCommand
from sublime import error_message, version
try:
    from .diagram import setup, process
except ValueError:
    from diagram import setup, process

def process_diagram_image(view):
    print("Processing diagrams in %s..." % view.file_name())

    if not process(view):
        error_message("No diagrams overlap selections.\n\n" \
            "Nothing to process.")

class DiagramContinueCreationThread(threading.Thread):

    def __init__(self, view):
        threading.Thread.__init__(self)

        self.view = view
        self.open_image = True
        self.sleepEvent = threading.Event()

    def run(self):
        view = self.view
        window = view.window()

        # Force it to be refreshed on the first time
        change_count = -1
        current_time = time.perf_counter()

        elapsed_time = 0.1
        mininum_time = 1.0
        default_time = 1.0

        while True:
            print("current_time: %s" % current_time)

            # Run until it closes
            if view not in window.views():
                print("Exiting continuous thread...")
                return

            elif change_count != view.change_count() \
                    and window == sublime.active_window() \
                    and view == window.active_view():

                current_time = time.perf_counter()
                change_count = view.change_count()

                active_sheet = window.active_sheet()
                group, view_index = window.get_view_index(view)

                if not process(view, self):
                    error_message("No diagrams overlap selections.\n\n" \
                        "Nothing to process.")

                window.focus_view( view )
                window.focus_group( group )
                window.focus_sheet( active_sheet )

            elapsed_time = current_time - time.perf_counter()
            self.sleepEvent.wait( elapsed_time*3 if elapsed_time > mininum_time else default_time )


class DisplayDiagramsContinually(TextCommand):

    def run(self, edit):
        print("Processing diagrams in %s..." % self.view)

        continuous_thread = DiagramContinueCreationThread( self.view )
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
