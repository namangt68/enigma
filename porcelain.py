__author__ = 'enitihas & swappy'

from plumber import *
import getopt
import os
import sys
from files import get_all_files
import tempfile
import subprocess as sb
import config

def cmd_add(args):
    opts , args = getopt.getopt(args, 'a', ["all"])
    if not (args or opts):
        print("""Nothing specified, nothing added.
Maybe you wanted to say 'eni add .'?""")
    add_all = False
    for options in opts:
        if options[0] in ('-a','--all'):
            add_all = True
        else:
            print('Unrecognized Option {}'.format(options[0]))
            print('Please see help for directions on how to use.')
            sys.exit(0)
    if '.' in args:
        add_all = True
    if add_all:
        all_files = get_all_files(repo_dir)
        for file in all_files:
            git_write_hash_file(file)
            git_update_index(file)
    else:
        cwd = os.getcwd()
        abs_path_args = [os.path.join(cwd, x) for x in args]
        for name, abs_name in zip(args,abs_path_args):
            if not os.path.exists(abs_name):
                print("fatal: pathspec '{}' did not match any files".format(name))
            if os.path.isdir(abs_name):
                all_files = get_all_files(abs_name)
                for file in all_files:
                    git_write_hash_file(file)
                    git_update_index(file)
            else:
                git_write_hash_file(abs_name)
                git_update_index(abs_name)


def cmd_init(args):
    if args:
        git_init(args)
    else:
        git_init()

def cmd_commit(args):
    opts , args = getopt.getopt(args, '', ["message="])
    for option in opts:
        if option[0] == '--message=':
            git_commit(option[1])
            return None
    commit_file = tempfile.NamedTemporaryFile(mode='r')
    sb.call([config.editor,commit_file.name])
    commit_message = commit_file.read()
    commit_file.close()
    git_commit(commit_message)

def cmd_status(args):
    modified , added, untracked = git_changed_files()
    print("On branch {}\n".format(curr_branch_name))
    #TODO: print "Initial Commit" here if no prior commit done
    if added:
        print(
            """Changes to be committed:
    (use "eni rm --cached <file>..." to unstage)

            """
        )
        for file in added:
            print('\t\tnew file:   {}'.format(file))
    if modified:
        print(
            """Changes not staged for commit:
  (use "eni add <file>..." to update what will be committed)
  (use "eni checkout -- <file>..." to discard changes in working directory)

            """
        )
        for file in modified:
            print('\t\tmodified:   {}'.format(file))
    if untracked:
        print("""Untracked files:
  (use "eni add <file>..." to include in what will be committed)

            """)
        for file in untracked:
            print('\t\tmodified:   {}'.format(file))


commands = {
    'add': cmd_add,
    'commit': cmd_commit,
    'init': cmd_init,
    'status': cmd_status
}

def main():
    argv = sys.argv[1:]
    for command in commands:
        if command.startswith(argv[0]):
            commands[command](argv[1:])
            sys.exit(0)
    print("Not a valid git command {}".format(argv[1]))

if __name__ == '__main__':
    config.ignore_list = read_file(os.path.join(git_dir,'.eniignore')).strip().split('\n') + ['.eni']
    main()
