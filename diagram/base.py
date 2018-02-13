import sys

class BaseDiagram(object):
    def __init__(self, processor, sourceFile, text):
        self.uml_processor = processor
        self.text = text
        self.sourceFile = sourceFile

    def generate(self):
        raise NotImplementedError('abstract base class is abstract')


class BaseProcessor(object):
    DIAGRAM_CLASS = None
    CHARSET = None
    CHECK_ON_STARTUP = True
    NEW_FILE = False

    def load(self):
        raise NotImplementedError('abstract base class is abstract')

    def extract_blocks(self, view):
        raise NotImplementedError('abstract base class is abstract')

    def process(self, sourceFile, text_blocks, sequence):
        diagrams = []

        for block in text_blocks:
            try:
                print("Rendering diagram for block...", sequence[0])
                diagram = self.DIAGRAM_CLASS(self, sourceFile, block, sequence[0])
                rendered = diagram.generate()
                diagrams.append(rendered)
            except Exception as e:
                print(repr(block))
                print("Error rendering diagram for block: %r" % e)
                sys.excepthook(*sys.exc_info())
            sequence[0] += 1

        return diagrams


class BaseViewer(object):
    def load(self):
        raise NotImplementedError('abstract base class is abstract')

    def view(self, filenames):
        raise NotImplementedError('abstract base class is abstract')
