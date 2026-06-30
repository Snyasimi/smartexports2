from abc import ABC,abstractmethod

class EltSerivceInterface(ABC)

    @abstractmethod
    def extract_data(self):
        #Extract data from source
        pass

    @abstractmethod
    def transform_data(self):
        #Transform data before loading/saving
        pass

    @abstractmethod(self):
    def load_data:
        #Load data to neo4J
        pass

