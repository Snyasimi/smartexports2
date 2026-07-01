from abc import ABC,abstractmethod

class ELTServiceInterface(ABC):

    @abstractmethod
    def extract_data(self):
        #Extract data from source
        pass

    @abstractmethod
    def transform_data(self):
        #Transform data before loading/saving
        pass

    @abstractmethod    
    def load_data(self):

        #Load data to neo4J
        pass

