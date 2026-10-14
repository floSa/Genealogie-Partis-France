from pagestore import PageStore
from wikiclient import Client


def store(client=None):
    return PageStore(client or Client())
