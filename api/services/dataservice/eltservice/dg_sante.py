from .interface.py import ELTService


class DgSante(ELTServiceInterface):
    
    links = [

            {
                "active_substance_download:"{
                    "link":"https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/active-substances-download?format=json&api-version=v3.0",
                    "headers":{"Content-Type":"application/json"},
                    "params": {"format":"json"}
                    },
                ""
                    
                ]

    def extract_data(self,links):


