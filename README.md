Marking Assistant
=================

A command line tool to help mark assignments for a particular course I tutor.

## Setup

1. `pip install begins`.

2. Put the TODO.py file inside the same directory as each of the `P01`/`P02`/etc directories, or put in a symlink.

3. Initialise the marks storage:

```
$ ./TODO.py init
```

This will search through each of the `P??` directories to find students' scripts, and create a JSON file to store marks and comments (called `marks.json` by default, but the `--marks-file` flag can change that).

Because it's saved as a JSON file, you can store backups! Especially because this tool is in the experimental phase, and so it's not my fault if it loses all your data.

If a marks file already exists, then `./TODO.py init` will find any new scripts, and leave existing marks unchanged.

Also add a `checklist.json` file into the current directory.

## Usage

* Get some help:

```
$ ./TODO.py [-h|--help]
$ ./TODO.py {command} -h   # Get help on a particular command.
```

* Get a colour-coded list of which files have been marked and which haven't:

```
$ ./TODO.py status
```

* Pick a script at random to mark (think of it as a lucky dip):

```
$ ./TODO.py random                # Chooses any random unmarked script
$ ./TODO.py random P04            # Chooses a random unmarked script from P04
$ ./TODO.py random P04 P10 P11    # Chooses a random unmarked script from P04 or P10 or P11
```

* Add/edit marks and comments to a script, using your favourite `$EDITOR`:

```
$ ./TODO.py mark P01/s1234567.py
```

If marks/comments already exist, they will be inserted into the editor and allow you to edit the changes.

* List names/IDs of students in a given prac: (do this when you need to write their names down on a whiteboard or something)

```
$ ./TODO.py list P01              # List in order of student number
$ ./TODO.py list P01 --random     # List in random order
```

* Export the marks/comments into the students' files:

```
$ ./TODO.py export P*/s*.py       # or list individual filenames
```

At the moment, there is no way to undo or re-export marks/comments. If no
final mark/meeting comment/general comment exists, that field will be
silently left blank in the student's script.

## Future work

* Improve `status` to better report various states of a file: (unmarked, code marked, final marked); (uninterviewed, interviewed, absent).
* Report postgraduate students in the editor.

(Also see the open issues.)

Stretch goals include:

* Embedding commands to run the test script. (Be aware that the test script will change slightly from semester to semester, and this shouldn't cause issues)
* Statistics reporting on the marks.
