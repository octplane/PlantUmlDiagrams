from __future__ import absolute_import
from .base import BaseDiagram
from .base import BaseProcessor
from subprocess import Popen as execute, PIPE, STDOUT, call
from os import getcwd, chdir
from os.path import abspath, dirname, exists, isdir, join, splitext, basename

from tempfile import NamedTemporaryFile
from sublime import platform, load_settings

import plantuml_connection

import os
import sys
import subprocess

if sys.version_info < (3,0):
    DEVNULL = open(os.devnull, 'wb')
else:
    from subprocess import DEVNULL

if os.name == 'nt':
    from ctypes import windll, create_unicode_buffer

IS_MSWINDOWS = (platform() == 'windows')
CREATE_NO_WINDOW = 0x08000000  # See MSDN, http://goo.gl/l4OKNe
EXTRA_CALL_ARGS = {'creationflags': CREATE_NO_WINDOW, 'shell': True} if IS_MSWINDOWS else {}

# Support [png, svg, txt, utxt, latex] output image formats
# https://github.com/jvantuyl/sublime_diagram_plugin/pull/59
# https://github.com/jvantuyl/sublime_diagram_plugin/issues/47
OUTPUT_FORMAT_DICT = \
{
    'png': '.png',
    'svg': '.svg',
    'txt': '.txt',
    'utxt': '.utxt',
    'pdf': '.pdf',
    'vdx': '.vdx',
    'eps': '.eps',
    'latex': '.tex',
    'latex:nopreamble': '.tex',
}


class PlantUMLDiagram(BaseDiagram):
    def __init__(self, processor, sourceFile, text, sequence=0):
        super(PlantUMLDiagram, self).__init__(processor, sourceFile, text)

        self.sourceFile = sourceFile
        self.output_format = self.uml_processor.OUTPUT_FORMAT
        self.output_extension = OUTPUT_FORMAT_DICT.get(self.output_format, None)

        if not self.output_extension:
            raise Exception("Unsupported value '%s' for setting 'output_format': %s" % (
                    self.output_format, self.output_extension))

        if self.sourceFile is None:
            self.file = NamedTemporaryFile(prefix='untitled', suffix=self.output_extension, delete=False)
            self.sourceFile = self.file.name

        else:

            if self.uml_processor.NEW_FILE:
                self.file = NamedTemporaryFile(prefix=self.sourceFile, suffix=self.output_extension, delete=False)

            else:
                self.sourceFile = "%s%s%s" % (splitext(self.sourceFile)[0], str(sequence) if sequence else "", self.output_extension)
                self.file = open(self.sourceFile, 'wb')

    def __str__(self):
        return "Diagram of %s(%s, %s)" % ( self.sourceFile, self.output_format, self.output_extension )

    def __del__(self):
        super( PlantUMLDiagram, self ).__del__()
        self.file.close()

    def generate(self):
        """
        Set the dir of sourceFile as working dir, otherwise plantuml could not include files correctly.
        """

        try:
            sublime_settings = load_settings("PlantUmlDiagrams.sublime-settings")
            server_url = sublime_settings.get('plantuml_server', 'http://www.plantuml.com/plantuml/')
            self._generate_server( "%s/%s/" % (server_url.strip('/'), self.output_format))

        except Exception as error:
            print("Failed to connect to the server: %s (%s) Falling back to local rendering..." % (error, server_url))
            cwd, startupinfo = self._get_local_dir_info()
            self._generate_local(cwd, startupinfo)

        return self.file

    def _generate_server(self, server_url):
        plantumlserver = plantuml_connection.PlantUML(server_url)
        content = plantumlserver.processes(self.text.encode('utf-8'))
        self.file.write(content)

    def _generate_local(self, cwd, startupinfo):
        """
            http://en.plantuml.com/command-line
        """
        command = [
            'java',
            '-DPLANTUML_LIMIT_SIZE=50000', # max output image height
            '-jar',
            self.uml_processor.plantuml_jar_path,
            '-pipe',
            '-t%s' % self.output_format,
        ]

        charset = self.uml_processor.CHARSET

        if charset:
            # print('using charset: ' + charset)
            command.append("-charset")
            command.append(charset)

        else:
            # print('using default charset: UTF-8')
            command.append("-charset")
            command.append('UTF-8')

        # print("Command: %s" % (command))

        puml = execute(
            command,
            stdin=PIPE,
            stdout=self.file,
            stderr=PIPE,
            startupinfo=startupinfo,
            cwd=cwd,
            env=os.environ,
            **EXTRA_CALL_ARGS
        )
        output = puml.communicate(input=self.text.encode('UTF-8'))

        if puml.returncode != 0:
            new_data = []

            for data in output:

                if data:
                    data = data.decode('UTF-8')
                    data = data.replace('\r\n', '\n').rstrip(' \n\r')
                    new_data.append(data)

            print(self.text)
            print("Error Processing Diagram:", ''.join(new_data))
            return

    def _get_local_dir_info(self):
        cwd = dirname(self.sourceFile)

        if not isdir(cwd):
            cwd = getcwd()

        startupinfo = None

        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            # Make sure the cwd is ascii
            try:
                cwd.encode('mbcs')

            except UnicodeEncodeError:
                buf = create_unicode_buffer(512)
                if windll.kernel32.GetShortPathNameW(cwd, buf, len(buf)):
                    cwd = buf.value
        return cwd, startupinfo


class PlantUMLProcessor(BaseProcessor):
    DIAGRAM_CLASS = PlantUMLDiagram

    def __str__(self):
        return "Plant UML Processor"

    def load(self):
        self.check_dependencies()
        self.find_plantuml_jar()

        if self.CHECK_ON_STARTUP:
            self.check_plantuml_functionality()

    def check_dependencies(self):
        has_java = call(
            ["java", "-version"],
            **EXTRA_CALL_ARGS
        )

        if has_java is not 0:
            raise Exception("can't find Java")

    def check_plantuml_functionality(self):
        puml = execute(
            [
                'java',
                '-jar',
                self.plantuml_jar_path,
                '-testdot'
            ],
            stdout=PIPE,
            stderr=STDOUT,
            stdin=DEVNULL,
            **EXTRA_CALL_ARGS
        )

        (stdout, stderr) = puml.communicate()
        dot_output = str(stdout)

        print("PlantUML Smoke Check:")
        print(dot_output)

        if ('OK' not in dot_output) or ('Error' in dot_output):
            raise Exception('PlantUML does not appear functional')

    def find_plantuml_jar(self):
        self.plantuml_jar_file = 'plantuml.jar'
        self.plantuml_jar_path = None

        self.plantuml_jar_path = abspath(
            join(
                dirname(__file__),
                self.plantuml_jar_file
            )
        )

        if not exists(self.plantuml_jar_path):
            sublime_settings = load_settings("PlantUmlDiagrams.sublime-settings")
            self.plantuml_jar_path = abspath(sublime_settings.get('jar_file'))
            self.plantuml_jar_file = basename(self.plantuml_jar_path)

            if not exists(self.plantuml_jar_path):
                raise Exception("can't find " + self.plantuml_jar_file)

        # print("Detected %s" % (self.plantuml_jar_path,))

    def check_plantuml_version(self):
        puml = execute(
            [
                'java',
                '-jar',
                self.plantuml_jar_path,
                '-version'
            ],
            stdout=PIPE,
            stderr=STDOUT,
            stdin=DEVNULL,
            **EXTRA_CALL_ARGS
        )

        (stdout, stderr) = puml.communicate()
        version_output = stdout

        print("Version Detection:")
        print(version_output)

        if not puml.returncode == 0:
            raise Exception("PlantUML returned an error code")

    def extract_blocks(self, view):
		# If any Region is selected - trying to convert it, otherwise converting all @start-@end blocks in view
        sel = view.sel()
        if sel[0].a == sel[0].b:
            pairs = (
                    (start, view.find('@end', start.begin()),)
                    for start in view.find_all('@start')
                )
            return (view.full_line(start.cover(end)) for start, end in pairs)
        else:
            return sel
