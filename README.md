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

* Add/edit a code mark and general comments to a script:

```
$ ./TODO.py mark P01/s1234567.py
```

* List names/IDs of students in a given prac: (do this when you need to write their names down on a whiteboard or something)

```
$ ./TODO.py list P01              # List in order of student number
$ ./TODO.py list P01 --random     # List in random order
```

## Future work

* Add the following commands:
  * `interview`, to make meeting comments and assign a final mark.
  * `export`, to insert the comments and grades into the students' files.
* Add a command and/or modify `init` to allow for the addition of late scripts.

Stretch goals include:

* Embedding commands to run the test script. (Be aware that the test script will change slightly from semester to semester, and this shouldn't cause issues)
* Statistics reporting on the marks.
