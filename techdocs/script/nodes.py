import os


# Does not check the file on disk, but uses the path to determine the type
def looks_fileish(fspath):
    return not looks_dirish(fspath)


def looks_dirish(fspath):
    return fspath.endswith("/") or fspath.endswith("*") or fspath == "."


def looks_wildcardish(fspath):
    return "*" in fspath
