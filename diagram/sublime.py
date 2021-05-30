#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


from .base import BaseViewer
import sublime

class SublimeViewer(BaseViewer):
	def __str__(self):
		return "Sublime Simple Viewer"

	def load(self):
		if not sublime.version().startswith(('3','4')):
			raise Exception("Sublime version not supported!")

	def view(self,diagram_files):
		for diagram_file in diagram_files:
			if diagram_file:
				sublime.active_window().open_file(diagram_file.name)
