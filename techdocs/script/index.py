import json
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from os import path


class FileIndex:
    def __init__(self, items: tuple):
        self.items = items
        self.removed = ()

    def add(self, item):
        for existing_item in self.items:
            # If it's not the same file, keep looking
            if item.file != existing_item.file:
                continue
            # If it's the same file coming from the same repo, do nothing, just return
            if item.repo == existing_item.repo:
                return
            # If it's the same file coming from a different repo, raise an error
            raise FileIndexError(
                f"The file {item.file} is already indexed from repository {existing_item.repo}"
            )
        # If the loop ends, it means the file is not indexed yet, so add it
        self.items = self.items + (item,)

    def remove(self, item):
        removed = tuple(filter(lambda existing_item: existing_item.file == item.file, self.items))
        self.items = tuple(
            filter(lambda existing_item: existing_item.file != item.file, self.items)
        )
        self.removed = self.removed + removed


@dataclass
class FileIndexItem:
    file: str
    repo: str


class FileIndexLoader:
    @classmethod
    def load(cls, fspath, fs):
        items = []
        for file in fs.scan(fspath, ".*"):
            cnt = json.loads(fs.read_string(path.join(fspath, file)))
            items.append(FileIndexItem(cnt["file"], cnt["repo"]))
        return FileIndex(tuple(items))

    @classmethod
    def save(cls, index, fspath, fs):
        for item in index.items:
            fs.write_string(
                path.join(fspath, item.repo, hash(item.file)),
                json.dumps({"file": item.file, "repo": item.repo}),
            )
        for removed in index.removed:
            fs.delete(path.join(fspath, removed.repo, hash(removed.file)))

    @classmethod
    @contextmanager
    def loaded(cls, fspath, fs, save=True):
        index = cls.load(fspath, fs)
        yield index
        if save:
            cls.save(index, fspath, fs)


class FileIndexError(Exception):
    pass


def hash(some_str):
    return sha256(some_str.encode()).hexdigest()
