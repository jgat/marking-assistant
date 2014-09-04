#!/usr/bin/env python
""" Marking assistant

Dependencies (pip install):
* begins
"""

import json
import os
import random
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

MARK_EDITOR_DEFAULT = '''# Enter mark and comments for {filename}.
# Lines beginning with # are discarded.
# If the 'Total: ' line is left blank, no code mark will be assigned.{notice}

Total: {mark}

General comments:

{comments}'''


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
        self.code = None

        self.code_mark = self.final_mark = None
        self.comments = self.meeting_comments = ''

    def is_marked(self):
        "Return True if the 'code mark' has been recorded."
        return self.code_mark is not None

    def get_mark(self):
        "Return the final mark, or the code mark if final mark doesn't exist."
        if self.final_mark is None:
            return self.code_mark
        else:
            return self.final_mark

    def read(self):
        "Read and return the contents of the student's script"
        if self.code is None:
            with open(self.filename, 'rU') as f:
                self.code = f.read()
        return self.code

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
    def __init__(self, scripts):
        self.scripts = list(scripts)

    def to_json(self):
        "Serialise this object."
        return [s.to_json() for s in self.scripts]

    @classmethod
    def from_json(cls, data):
        "Deserialise an instance of this class."
        return cls(Script.from_json(d) for d in data)

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
        if scripts is None:
            scripts = self.scripts
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
             "".format(filename))

    editor = os.environ.get('EDITOR') or 'vim'
    with open(filename, 'w') as f:
        print >> f, initial
    subprocess.call([editor, filename])
    with open(filename, 'r') as f:
        text = f.read()
    return text


def edit_marks(script_name, mark, comments):
    """Allow the grader to edit marks. Return the new mark and comments."""
    notice = ''
    if mark is not None or comments != '':
        notice = ('\n\n# Note that the following mark/comment already exists '
                  'for this student.\n# Edits to this will overwrite the '
                  'existing mark/comment.')

    # Make sure the editor file doesn't contain the word 'None'
    if mark is None:
        mark = ''

    initial = MARK_EDITOR_DEFAULT.format(filename=script_name, mark=mark,
                                         comments=comments, notice=notice)
    text = editor_input(EDITOR_FILE, initial)

    # Remove lines beginning with #
    text = '\n'.join(line for line in text.split('\n') if not line.startswith('#'))

    # Find the new mark:
    for line in text.splitlines():
        if line.startswith('Total:'):
            total = line.split(':', 1)[1].strip()
            if total == '':
                newmark = None
            elif total.isdigit():
                newmark = int(total)
            else:
                fail("Error: Mark {!r} is not an integer >= 0.\n"
                     "Edits are saved in the file: {}\n"
                     "Exiting without applying changes..."
                     "".format(total, EDITOR_FILE))
            break
    else:
        fail("Error: No 'Total:' line was found.\n"
             "Edits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))
        sys.exit(1)

    # Find the comments
    newcomments = text.partition('General comments:')[2].strip()
    if '"""' in newcomments:
        fail('Error: Comments cannot contain """.\n'
             "Edits are saved in the file: {}\n"
             "Exiting without applying changes...".format(EDITOR_FILE))

    os.remove(EDITOR_FILE)
    return newmark, newcomments


##############################
# Definitions of each subcommand in the application.
##############################

@begin.subcommand
def init(force=False):
    "Initialise the marks file."
    if MAIN.scripts is not None and not force:
        fail("Marks file is already initialised. Use --force to start from scratch.")

    cwd = os.getcwd()

    # Find all pracs which are in this folder
    pracs = []
    for f in os.listdir(cwd):
        # Add directories of the form P{01,02,...}
        full = os.path.join(cwd, f)
        if os.path.isdir(full) and re.match(r'^P\d{2}$', f):
            pracs.append(f)

    # Find all student scripts within those pracs
    students = []
    for p in pracs:
        # Add files of the form s*.py
        for s in os.listdir(p):
            if re.match(r'^s\d+\.py$', s):
                students.append(os.path.join(p, s))

    s = ScriptSet(Script(s) for s in students)
    MAIN.save(s)


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
            print GRE + "{:<15} {:>4}    {}".format(f, mark, comments).rstrip() + DEF
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
        print random.choice(options).filename


pick_random.__name__ = 'random'  # Workaround for a bug in the begins library


@begin.subcommand
def mark(script):
    "Mark a student's script."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")

    if script not in MAIN.scripts:
        fail("No script {} in marks file.".format(script))

    script = MAIN.scripts[script]
    mark, comments = edit_marks(script.filename, script.code_mark,
                                script.comments)
    script.code_mark = mark
    script.comments = comments
    MAIN.save()


@begin.subcommand
def interview(script):
    "Make interview comments/marks."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")
    raise NotImplementedError()


@begin.subcommand(name='list')
def list_students(prac, random=False):
    "List all student names in a given prac. Useful when writing names on whiteboard at start of pracs."
    if MAIN.scripts is None:
        fail("Marks file not found. Run ./TODO.py init")
    raise NotImplementedError()


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
