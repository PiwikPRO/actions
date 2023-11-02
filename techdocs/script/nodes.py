import os


# Does not check the file on disk, but uses the path to determine the type
def looks_fileish(fspath):
    return "." in os.path.basename(fspath)

def looks_dirish(fspath):
    return not looks_fileish(fspath)
