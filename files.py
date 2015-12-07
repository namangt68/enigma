import os
import fnmatch
import config

def get_all_files(dirpath):
    print(config.ignore_list)
    file_list = []
    entries = os.listdir(dirpath)
    abs_entries = [os.path.join(dirpath,x) for x in entries]
    for entry, abs_entry in zip(entries, abs_entries):
        for pattern in config.ignore_list:
            if fnmatch.fnmatch(entry, pattern) or fnmatch.fnmatch(abs_entry, pattern):
                print(entry,abs_entry,pattern)
                break
            else:
                if os.path.isfile(abs_entry):
                    file_list.append(abs_entry)
                elif os.path.isdir(abs_entry):
                    file_list += get_all_files(abs_entry)
    return file_list
