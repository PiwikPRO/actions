from hashlib import sha256


def hashb(data):
    return sha256(data).hexdigest()
