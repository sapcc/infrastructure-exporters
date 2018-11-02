from abc import ABC, abstractmethod

class Exporter(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def collect(self):
        pass

    def export(self):
        pass