#!/usr/bin/env python
""" Marking assistant

Dependencies (pip install):
* begins
"""

import json
import os
import random
import re
import sys

import begin

DEF = "\033[1;0m"
RED = "\033[1;31m"
GRE = "\033[1;32m"
YEL = "\033[1;33m"
BLU = "\033[1;34m"

MARKS_FILE = 'marks.json'


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
        self.comments = self.meeting_comments = None

    def get_mark(self):
        "Return the student's final mark or code mark, whichever exists"
        if self.final_mark is None:
            return self.code_mark
        return self.final_mark

    def set_code_mark(self, mark):
        self.code_mark = mark

    def is_marked(self):
        "Return True if the 'code mark' has been recorded."
        return self.code_mark is not None

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


##########

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


##########
# Tools for executing the script, and commands:
##########

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


@begin.subcommand
def init(force=False):
    "Initialise the marks file."
    if MAIN.scripts is not None and not force:
        print >> sys.stderr, "Marks file is already initialised. Use --force to start from scratch."
        sys.exit(1)

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
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)

    done = 0
    for s in MAIN.scripts:
        if s.is_marked():
            print GRE + s.filename + DEF
            done += 1
        else:
            print RED + s.filename + DEF
    print YEL + "Total: {}/{}".format(done, len(MAIN.scripts)) + DEF


@begin.subcommand(name='random')
def pick_random(*prac):
    "Pick a random unmarked script to mark next."
    if MAIN.scripts is None:
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)

    options = [s for s in MAIN.scripts if not s.is_marked()
               and (not prac or s.prac in prac)]

    if not options:
        print GRE + "All done! \o/" + DEF
    else:
        print random.choice(options).filename
pick_random.__name__ = 'random'  # Workaround for a bug in the begins library


@begin.subcommand
def mark(script, force=False):
    "Mark a student's script."
    if MAIN.scripts is None:
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)

    if script not in MAIN.scripts:
        print >> sys.stderr, "No script {} in marks file.".format(script)
        sys.exit(1)

    script = MAIN.scripts[script]
    if script.is_marked() and not force:
        print >> sys.stderr, "Script is already marked. Use --force to overwrite."
        sys.exit(1)

    x = int(raw_input("Mark /10: "))
    script.set_code_mark(x)
    MAIN.save()


@begin.subcommand
def interview(script):
    "Make interview comments/marks."
    if MAIN.scripts is None:
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)
    raise NotImplementedError()


@begin.subcommand(name='list')
def list_students(prac, random=False):
    "List all student names in a given prac. Useful when writing names on whiteboard at start of pracs."
    if MAIN.scripts is None:
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)
    raise NotImplementedError()
list_students.__name__ = 'list'  # Workaround for a bug in the begins library


@begin.subcommand
def export(script):
    "Write the student's marks/comments into their file."
    if MAIN.scripts is None:
        print >> sys.stderr, "Marks file not found. Run ./TODO.py init"
        sys.exit(1)
    raise NotImplementedError()


@begin.start
def run(marks_file=MARKS_FILE):
    "Marking assistant."
    # globals are ok if you know what you're doing
    global MAIN
    MAIN = Main(marks_file)
    MAIN.load()
