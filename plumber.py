import hashlib
import re
import zlib
import os
import sys
from pathlib import Path
import binascii
from files import get_all_files

def get_eni_dir():
    """
    Returns the full path of the .eni repository in which the current directory is being tracked.
    :return:full path of the .eni repository in which the current directory is being tracked.
    """
    cwd = os.getcwd()
    while '.eni' not in os.listdir(cwd):
        if cwd == '/':
            return None
        else:
            cwd = str(Path(cwd).parent)
    return os.path.join(cwd, '.eni')


def read_file(filename):
    file_object = open(filename)
    content = file_object.read()
    file_object.close()
    return content


eni_dir = get_eni_dir()
if eni_dir:
    eni_dir = os.path.abspath(eni_dir)
    repo_dir = str(Path(eni_dir).parent)
    repo_dir = os.path.abspath(repo_dir)
    curr_branch_path = read_file(os.path.join(eni_dir, 'HEAD'))[5:]
    curr_branch_name = curr_branch_path.split('/')[-1]
    curr_branch_blob_path = os.path.join(eni_dir,curr_branch_path)

def eni_relative_path(file_path):
    eni_dir = get_eni_dir()
    repo_dir = Path(eni_dir).parent
    repo_dir = os.path.abspath(repo_dir)
    return re.sub(repo_dir+r'/?', '', file_path)

def eni_changed_files():
    eni_dir = get_eni_dir()
    repo_dir = str(Path(eni_dir).parent)
    repo_dir = os.path.abspath(repo_dir)
    file_list = get_all_files(repo_dir)
    file_list = map(lambda x: os.path.abspath(x), file_list)
    file_list = map(lambda x: re.sub(repo_dir+r'/?', '', x), file_list)
    index_object = eni_read_index()
    modified_files = []
    added_files = []
    for entry in index_object:
        added_files.append(entry[1])
    cwd = os.getcwd()
    os.chdir(repo_dir)
    for entry in file_list:
        sha1_file = eni_hash_file(entry)
        should_be_path = os.path.join(eni_dir,'objects',sha1_file[:2], sha1_file[2:])
        if not os.path.exists(should_be_path):
            modified_files.append(entry)
    # TODO : Add provision for untracked files
    return modified_files, added_files , []


def eni_hash(content):
    """
    This function returns the sha1sum of the given string.
    It assumes that the given string is UTF-8
    :param content: Any string
    :return: SHA1 sum of the given string
    """
    digest = hashlib.sha1(content.encode('utf8'))
    return digest.hexdigest()


def eni_store(content, obj_type='blob'):
    """
    Returns the content to be stored in the eni object store for the given string.
    It does so by appending the headers specific to the blob type.
    :param content: The string which we need to store in .eni
    :param obj_type: The object type of the string, default is blob
    :return: The string which will be stored in the eni object store
    """
    header = "{} {}\0".format(obj_type, len(content))
    store = header + content
    return store


def eni_hash_file(filename):
    """
    Returns the sha1sum of the blob corresponding the the current content of the given file.
    :param filename: Any file
    :return:The sha1sum of the corresponding blob in the eni object store
    """
    content = read_file(filename)
    store = eni_store(content)
    return eni_hash(store)


def make_dir_if_not_exists(dir_name):
    """
    Makes a directory if by the given path if none such directory exists
    :param dir_name: Name of the directory we wish to create
    :return: Unit
    """
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)


def eni_write_hash_file(filename):
    """
    Writes a blob in the eni object store with the current contents of filename file.
    :param filename: The name of the file which we wish to store in the eni object store
    :return:
    """
    content = read_file(filename)
    store = eni_store(content)
    eni_write_hash(store)


def eni_write_hash(content):
    """
    Writes a blob in the eni object store with the given content.
    :param content: String to be stored
    :return: sha1sum of the blob created
    """
    hash_val = eni_hash(content)
    compressed_content = zlib.compress(content.encode('utf8'))
    eni_dir = get_eni_dir()
    write_dir = os.path.join(eni_dir, 'objects', hash_val[:2])
    make_dir_if_not_exists(write_dir)
    write_object = open(os.path.join(write_dir, hash_val[2:]), 'wb')
    write_object.write(compressed_content)
    write_object.close()
    return hash_val


def eni_get_content(file_name):
    """
    Returns the string contained in the given file in the directory .eni/objects
    :param file_name: fullpath to a blob in the eni object store
    :return:string stored in the blob
    """
    decompressed = eni_get_store(file_name)
    zero_pos = decompressed.index(b'\0')
    decoded = decompressed[zero_pos + 1:].decode('utf8')
    return decoded


def eni_get_blob_type(store):
    """
    Returns the type of blob stored in the given string
    :param store:Uncompressed value contained in a blob
    :return:Type of the blob
    """
    space_pos = store.index(b' ')
    return store[:space_pos].decode('utf8')


def eni_get_store(file_name):
    """
    Gets the decompressed value stored in the blob at given path
    :param file_name: full path of the blob
    :return:decompressed content in the blob
    """
    file_object = open(file_name, 'rb')
    file_content = file_object.read()
    file_object.close()
    decompressed = zlib.decompress(file_content)
    return decompressed


def eni_cat_file(sha1sum):
    """
    Returns the string to which the blob of sh1sum corresponds to.
    :param sha1sum: starting characters of the sha1sum of the blob whose real content we want to find
    :return:the string from which the blob was created.
    """
    # TODO: Raise an error when there exist two blobs starting with the same sha1sum
    sha_length = len(sha1sum)
    eni_dir = get_eni_dir()
    object_dir = os.path.join(eni_dir, 'objects')
    dirs = os.listdir(object_dir)
    dirs.remove('info')
    dirs.remove('pack')
    for directory in dirs:
        if directory == sha1sum[:2]:
            dir_name = os.path.join(object_dir, directory)
            for file in os.listdir(dir_name):
                if file[:sha_length - 2] == sha1sum[2:]:
                    return eni_get_content(os.path.join(dir_name, file))


def eni_init(path='.'):
    """
    Creates an empty .eni directory at the specified path
    :param path: Path at which the new .eni directory is to be created
    :return:
    """
    target_dir = os.path.join(path, '.eni')
    files = ['config', 'HEAD', 'description']
    os.mkdir(target_dir)
    os.chdir(target_dir)
    os.mkdir('branches')
    os.mkdir('refs')
    os.mkdir('objects')
    os.mkdir('hooks')
    os.mkdir('info')
    for file_name in files:
        open(file_name, 'a').close()
    head_file = open('HEAD','w')
    print('ref: refs/heads/master', file=head_file)
    head_file.close()
    os.chdir('objects')
    os.mkdir('info')
    os.mkdir('pack')
    os.chdir('..')
    os.chdir('refs')
    os.mkdir('heads')
    os.mkdir('tags')
    os.chdir('..')
    os.chdir('info')
    open('exclude', 'a').close()
    os.chdir('../..')


def eni_get_file_mode(file_name):
    """
    Returns the blob type of the given file
    :param file_name:
    :return:
    """
    # TODO: does nothing right now
    return 'mode'


def eni_read_index():
    """
    Read the current index of the repository and returns a dict.
    Keys of the dict are sha1sums
    Values in the dict are attributes about the file, such as mode and filename
    :return: dict containing sha1sums as keys and attributes of those files as values
    """
    eni_dir = get_eni_dir()
    index_file = os.path.join(eni_dir, 'index')
    if not os.path.exists(index_file):
        open(index_file, 'a').close()
    index_object = []
    with open(index_file) as f:
        for line in f:
            if line.strip() != '':
                entries = line.strip().split()
                index_object.append(entries)
    return index_object


def eni_write_index(index_object):
    """
    Writes to the index the given dictionary
    :param index_object: dict containing sha1sums as keys and attributes of those files as values
    :return:
    """
    eni_dir = get_eni_dir()
    index_file = os.path.join(eni_dir, 'index')
    index = open(index_file, 'w')
    for entry in index_object:
        for item in entry:
            print(item, end=' ', file=index)
        print('', file=index)
    index.close()


def eni_read_tree(filename):
    """
    Assumption: Parses tree_object from content
    :param filename: full path of the tree
    :return: tree_object containing list of lists
    """
    content = eni_get_content(filename)

    tree_object = []

    i = 0
    while i < len(content):
        entry_mode = ''
        while content[i] != ' ':
            entry_mode += content[i]
            i += 1

        entry_file_name = ''
        while content[i] != '\0':
            entry_file_name += content[i]
            i += 1

        entry_sha1 = ''
        j = 0
        while j < 20:
            entry_sha1 += content[j]
            j += 1
            i += 1
        sha1 = binascii.hexlify(entry_sha1.encode('utf8'))
        tree_object.append([entry_mode, entry_file_name, sha1.decode('utf8')])
    return tree_object

def eni_write_tree(tree_object):
    """
    Writes to the objects folder the given tree
    :param tree_object: dict containing sha1sums as keys and attributes of those files as values
    :return:
    """
    content = ''

    for entry in tree_object:
        content += entry[0] + ' ' + entry[1] + '\0' + binascii.unhexlify(entry[2])

    store = eni_store(content, 'tree')
    return eni_write_hash(store)


def eni_update_index(file_name):
    """
    Adds a file to the eni index for the next commit
    :param file_name:file to be staged
    :return:
    """
    index_object = eni_read_index()
    file_hash = eni_hash_file(file_name)
    file_mode = eni_get_file_mode(file_name)
    curr_file = [None] * 3
    curr_file[0] = file_mode
    curr_file[1] = file_name
    curr_file[2] = file_hash
    file_in_index = False
    for entry in index_object:
        if entry[1] == file_name:
            entry[2] = file_hash
            file_in_index = True
    if not file_in_index:
        index_object.append(curr_file)
    eni_write_index(index_object)


def eni_commit(commit_message):
    """
    Commits the current index file to the object store
    :param commit_message: The commit message for the current commit
    :return:
    """
    eni_dir = get_eni_dir()
    index_file = os.path.join(eni_dir, 'index')
    index_object = eni_read_index()
    hash_val = eni_write_tree(index_object)
    commit_content = '''tree {}
    author
    committer

    {}
    '''.format(hash_val, commit_message)
    eni_write_hash(eni_store(commit_content, 'commit'))
    index = open(index_file, 'w')
    index.close()
