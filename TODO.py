#!/usr/bin/env python
""" Marking assistant

Dependencies (pip install):
* begins
"""

import json
import os
from random import choice, shuffle
import re
import subprocess
import sys

import begin

DEF = "\033[1;0m"
RED = "\033[1;31m"
GRE = "\033[1;32m"
YEL = "\033[1;33m"
BLU = "\033[1;34m"

MARKS_FILE = 'marks.json'

EDITOR_FILE = '.mark-comment'

MARK_EDITOR_DEFAULT = '''# Enter mark and comments for {script.filename}.
# Lines beginning with # are discarded.
# If the 'mark' lines are left blank, no mark will be assigned.{notice}

Code mark: {script._code_mark_render}

General comments:

{script.comments}

----------------------------------------------

# This is the mark which will be entered into the student's file.
Final mark: {script._final_mark_render}

Meeting comments:

{script.meeting_comments}
'''


##############################
# Classes to manage data on students' marks.
##############################


class Script(object):
    "Keep track of marks/comments for a single student's script"
    def __init__(self, filename):
        match = re.match(r'^(P\d{2})/s\d+\.py$', filename)
        if not match:
            raise ValueError("Not a valid student's script: " + filename)
        self.filename = filename
        self.prac = match.group(1)

        # Keep some attributes to lazy evaluate
        self._code = None    # The text of the student's source
        self._name = None    # The student's name
        self._id = None      # The student's ID number

        self.code_mark = self.final_mark = None
        self.comments = self.meeting_comments = ''

    def is_marked(self):
        "Return True if the 'code mark' has been recorded."
        return self.code_mark is not None

    def has_edits(self):
        "Return True if the script has marks/comments"
        return (self.code_mark is not None or
                self.final_mark is not None or
                self.comments != '' or
                self.meeting_comments != '')

    def update(self, code_mark, final_mark, comments, meeting_comments):
        "Replace the marks/comments."
        self.code_mark = code_mark
        self.final_mark = final_mark
        self.comments = comments
        self.meeting_comments = meeting_comments

    def get_mark(self):
        "Return the final mark, or the code mark if final mark doesn't exist."
        if self.final_mark is None:
            return self.code_mark
        else:
            return self.final_mark

    def read(self):
        "Read and return the contents of the student's script"
        if self._code is None:
            with open(self.filename, 'rU') as f:
                self._code = f.read()
        return self._code

    def _get_from_file(self, token):
        "Retrieve a part of the file which immediately follows the given token"
        for line in self.read().splitlines():
            if token in line:
                return line.partition(token)[2].strip()
        raise SanityError("{} doesn't contain the string {!r}"
                          .format(self.filename, token))

    def get_name(self):
        "Return the student's name as listed in their code"
        if self._name is None:
            self._name = self._get_from_file('Student Name:')
        return self._name

    def get_id(self):
        "Return the student's ID number listed in their code"
        if self._id is None:
            self._id = self._get_from_file('Student Number:')
        return self._id

    # Make sure the editor file doesn't contain the word 'None'
    @property
    def _code_mark_render(self):
        return '' if self.code_mark is None else self.code_mark

    @property
    def _final_mark_render(self):
        return '' if self.final_mark is None else self.final_mark

    def to_json(self):
        "Serialise this object."
        return {'filename': self.filename,
                'code_mark': self.code_mark,
                'final_mark': self.final_mark,
                'comments': self.comments,
                'meeting_comments': self.meeting_comments}

    @classmethod
    def from_json(cls, data):
        "Deserialise an instance of this class."
        obj = cls(data['filename'])
        obj.code_mark = data['code_mark']
        obj.final_mark = data['final_mark']
        obj.comments = data['comments']
        obj.meeting_comments = data['meeting_comments']
        return obj

    def __repr__(self):
        return "Script({!r})".format(self.filename)


class ScriptSet(object):
    "Keeps track of marks data for all students."
    def __init__(self, scripts=None):
        scripts = scripts or []
        self.scripts = list(scripts)

    def add(self, script):
        "Adds a script. Silently ignore duplicates"
        if script.filename not in self:
            self.scripts.append(script)

    def sort(self):
        self.scripts.sort(key=lambda x: x.filename)

    def to_json(self):
        "Serialise this object."
        return [s.to_json() for s in self.scripts]

    @classmethod
    def from_json(cls, data):
        "Deserialise an instance of this class."
        x = cls(Script.from_json(d) for d in data)
        x.sort()
        return x

    def __iter__(self):
        return iter(self.scripts)

    def __len__(self):
        return len(self.scripts)

    def __getitem__(self, key):
        try:
            return next(s for s in self.scripts if s.filename == key)
        except StopIteration:
            raise KeyError("No script {} in marks file.".format(key))

    def __contains__(self, key):
        return any(s.filename == key for s in self.scripts)


##############################
# Tools used by the various commands in the script.
##############################

class SanityError(Exception):
    pass


class Main(object):
    "Top-level shared functionality"
    def __init__(self, marks_file):
        self.filename = marks_file
        self.scripts = None

    def load(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'rU') as f:
                self.scripts = ScriptSet.from_json(json.load(f))

    def save(self, scripts=None):
        scripts = scripts or self.scripts
        scripts.sort()
        with open(self.filename, 'w') as f:
            json.dump(scripts.to_json(), f)


def fail(msg, status=1):
    print >> sys.stderr, msg
    sys.exit(status)


def editor_input(filename, initial):
    """Open an editor containing the initial text, and return the text edited.

    Fails if the file already exists, but doesn't ever remove the file.
    """
    if os.path.exists(filename):
        fail("Temp file {!r} already exists.\n"
             "If it doesn't contain anything important, delete it."
             .format(filename))

    editor = os.environ.get('EDITOR') or 'vim'
    with open(filename, 'w') as f:
        print >> f, initial
    subprocess.call([editor, filename])
    with open(filename, 'r') as f:
        text = f.read()
    return text


def edit_marks(script):
    """Allow the grader to edit marks. Return the new mark and comments."""
    notice = ''
    if script.has_edits():
        notice = ('\n\n# Note that the following mark/comment already exists '
                  'for this student.\n# Edits to this will overwrite the '
                  'existing mark/comment.')

    initial = MARK_EDITOR_DEFAULT.format(script=script, notice=notice)
    text = editor_input(EDITOR_FILE, initial)

    # Remove lines beginning with #
    text = '\n'.join(line for line in text.split('\n')
                     if not line.startswith('#'))

    # Look for the code mark
    match = re.search(r'^Code mark:[ \t]*(\d*)[ \t]*$', text, re.M)
    if match is None:
        fail("Error: No valid 'Code mark' line was found.\nNext time, enter a"
             " single integer on the same line as 'Code mark:'.\n\n"
             "Edits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))
    code_mark = int(match.group(1)) if match.group(1) != '' else None

    # Look for the final mark
    match = re.search(r'^Final mark:[ \t]*(\d*)[ \t]*$', text, re.M)
    if match is None:
        fail("Error: No valid 'Final mark' line was found.\nNext time, enter a"
             " single integer on the same line as 'Final mark:'.\n\n"
             "Edits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))
    final_mark = int(match.group(1)) if match.group(1) != '' else None

    # Look for general comments
    match = re.search(r'^General comments:\s*(.*?)\s*-{40}', text, re.S | re.M)
    if match is None:
        fail("Error: No 'General comments:'.\nHow did you break that?"
             "\n\nEdits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))
    comments = match.group(1).strip()

    # Look for meeting comments
    match = re.search(r'^Meeting comments:\s*(.*)\s*', text, re.S | re.M)
    if match is None:
        fail("Error: No 'Meeting comments:' line.\nHow did you break that?"
             "\n\nEdits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))
    meeting_comments = match.group(1).strip()

    if '"""' in comments or '"""' in meeting_comments:
        fail('Error: Comments cannot contain """.\n\n'
             "Edits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))

    # Yay, the tutor didn't do anything silly.
    os.remove(EDITOR_FILE)
    script.update(code_mark, final_mark, comments, meeting_comments)


##############################
# Definitions of each subcommand in the application.
##############################

@begin.subcommand
def init():
    "Initialise the marks file."

    # Find all pracs which are in this folder
    pracs = []
    for f in os.listdir(os.getcwd()):
        # Add directories of the form P{01,02,...}
        if os.path.isdir(f) and re.match(r'^P\d{2}$', f):
            pracs.append(f)

    # Find all student scripts within those pracs
    students = []
    for p in pracs:
        # Add files of the form s*.py
        for f in os.listdir(p):
            full = os.path.join(p, f)
            if os.path.isfile(full) and re.match(r'^s\d+\.py$', f):
                students.append(full)

    scripts = MAIN.scripts or ScriptSet()

    found = 0
    for s in students:
        if s not in scripts:
            scripts.add(Script(s))
            print "Found new script: {}".format(s)
            found += 1

    if not found:
        print "No new scripts found."

    MAIN.save(scripts)


@begin.subcommand
def status():
    "Show summary of which scripts are marked/unmarked."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")

    done = 0
    print "Student:        Mark    General comments"
    for s in MAIN.scripts:
        f = s.filename
        comments = s.comments[:26].replace('\n', ' ')
        if len(s.comments) > 26:
            comments += '...'
        if s.is_marked():
            mark = s.get_mark()
            text = "{:<15} {:>4}    {}".format(f, mark, comments).rstrip()
            print GRE + text + DEF
            done += 1
        else:
            print RED + "{:<24}{}".format(f, comments).rstrip() + DEF
    print YEL + "Total: {}/{}".format(done, len(MAIN.scripts)) + DEF


@begin.subcommand(name='random')
def pick_random(*prac):
    "Pick a random unmarked script to mark next."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")

    options = [s for s in MAIN.scripts if not s.is_marked()
               and (not prac or s.prac in prac)]

    if not options:
        print GRE + "All done! \o/" + DEF
    else:
        print choice(options).filename
pick_random.__name__ = 'random'  # Workaround for a bug in the begins library


@begin.subcommand
def mark(script):
    "Mark a student's script."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")

    if script not in MAIN.scripts:
        fail("No script {} in marks file.".format(script))

    edit_marks(MAIN.scripts[script])
    MAIN.save()


@begin.subcommand(name='list')
def list_students(prac, random=False):
    """List all student names in a given prac.

    Useful when writing names on whiteboard at start of pracs.
    By default, outputs ordered by student ID.
    --random lists in a random order.
    """
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")

    scripts = [s for s in MAIN.scripts if s.prac == prac]

    if random:
        shuffle(scripts)

    for s in scripts:
        print "{:<30}{}".format(s.get_name(), s.get_id())
list_students.__name__ = 'list'  # Workaround for a bug in the begins library


@begin.subcommand
def export(script):
    "Write the student's marks/comments into their file."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")
    raise NotImplementedError()


@begin.start
def run(marks_file=MARKS_FILE):
    "Marking assistant."
    # globals are ok if you know what you're doing
    global MAIN
    MAIN = Main(marks_file)
    MAIN.load()
