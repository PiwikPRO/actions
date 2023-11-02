
import os
import re
import shutil


class Filesystem:

    def is_file(self, fspath):
        return os.path.isfile(fspath)
    
    def is_dir(self, fspath):
        return os.path.isdir(fspath)
    
    def copy(self, source, destination):
        shutil.copy(source, destination)

    def read_string(self, file):
        with open(file) as f:
            return f.read()
        
    def scan(self, directory, regex):
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames if re.match(regex, f)]



class MockFilesystem:

    def __init__(self, files: dict, relpath:str="/"):
        self.relpath = relpath
        self.files = files

    def is_file(self, fspath):
        return fspath in self.files
    
    def is_dir(self, fspath):
        return any([f.startswith(fspath) for f in self.files])
    
    def copy(self, source, destination):
        if source not in self.files:
            raise FileNotFoundError(f"File {source} not found")
        self.files[destination] = self.files[source]

    def read_string(self, file):
        if file not in self.files:
            raise FileNotFoundError(f"File {file} not found")
        return self.files[file]
    
    def scan(self, directory, regex):
        return [f[len(directory)+(0 if directory.endswith("/") else 1):] for f in self.files.keys() if f.startswith(directory) and re.match(regex, f)]
