import requests
import json
from interface import ELTServiceInterface


class DgSante(ELTServiceInterface):
    
    links = {
        "active_substance_download": {
            "link": "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/active-substances-download?format=json&api-version=v3.0",
            "headers": {"Content-Type": "application/json"},
            "params": {"format": "json"}
        },

        "pesticide_residue_mrls_download": {
            "link": "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues-mrls?format=json&api-version=v3.0",
            "params": {"format": "json"}
        },

        "pesticide_residues": {
            "link": "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues?pesticide_residue_lg=EN&format=json&api-version=v3.0",
            "params": {"format": "json", "pesticide_residue_lg": "EN"}
        },

        "pesticide_residue_products": {
            "link": "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues-products?language=EN&format=json&api-version=v3.0",
        }
    }
    
    def get_active_substances(self):
        
        substances = []
        
        response = requests.get(self.links["active_substance_download"]["link"])
        counter = 0
        
        for line in response.iter_lines():
            line = line.decode("utf-8")
            obj = json.loads(line)
            
            substance = {
                "substance_id": obj.get("substance_id"),
                "substance_name": (obj.get("substance_name") or "").strip(),
                "substance_status": (obj.get("substance_status") or "").strip(),
                "substance_exp_date": (obj.get("expiry_date") or "").strip(),
                "substance_approval_date": (obj.get("approval_date") or "").strip(),
                "pesticide_residue_linked": (obj.get("pesticide_residue_linked") or "").strip(),
                "pesticide_residue_linked_annex": (obj.get("pest_res_linked_annex") or "").strip(),
            }
            
            substances.append(substance)
        
            
            #print(f"Substance_id:{obj.get('substance_id')}")
            if counter > 1:
                break
            #print(substance)
            counter +=1 
            
            #print(substances)
            return substances
    
    def get_pest_residues(self):
        counter = 0 
        
        pest_residues = []
        
        response = requests.get(self.links["pesticide_residues"]["link"])
       
        residues = response.json()
        
        for obj in residues.get("value", []):
            if counter > 1:
                break
            residue = {
                "residue_id": int(obj["pesticide_residue_id"]),
                "residue_name": (obj.get("pesticide_residue_name") or "").strip(),
                "language": (obj.get("pesticide_residue_lg") or "").strip(),
                "footnote_code": (obj.get("pesticide_residue_footnote_code") or "").strip(),
                "footnote_definition": (obj.get("pesticide_residue_footnote_def") or "").strip(),
                "footnote_text": (obj.get("pesticide_residue_footnote_txt") or "").strip(),
                "version": int(obj["pesticide_residue_version_nbr"]),
                "original_residue_id": obj.get("original_pesticide_residue_id")
            }
            
            pest_residues.append(residue) 
            #counter += 1
        #print(pest_residues)
        
        return pest_residues
        
        
        pass
    def get_pest_residue_products(self):
        counter = 0
        response = requests.get(self.links["pesticide_residue_products"]["link"])
       
        pest_products = []
        products = response.json()

        for obj in products.get("value", []):
            if counter > 1:
                break

            product = {
                "product_id": int(obj["product_id"]),
                "parent_product_id": obj.get("product_parent_id"),
                "product_code": (obj.get("product_code") or "").strip(),
                "product_type_id": int(obj["product_type_id"]),
                "product_name": (obj.get("product_name") or "").strip(),
                "scientific_names": (obj.get("product_scientific_names") or "").strip(),
                "synonym_names": (obj.get("product_synonym_names") or "").strip(),
                "language": (obj.get("language") or "").strip(),
            }

            pest_products.append(product)

            counter += 1
            #counter += 1
        #print(pest_products)
        
        return pest_products
    
    def get_pest_residue_mrl():
        pass
    

    def extract_data(self):
        active_substances = self.get_active_substances()
        pest_residues = self.get_pest_residues()
        pest_residue_products = self.get_pest_residue_products()
        
        print([active_substances, pest_residues, pest_residue_products])
        
        return {
                    "substances": substances,
                    "residues": residues,
                    "products": products,
                 }
            
            

            
            
            
    def load_data(self):
        pass
    def transform_data(self):
        pass
    
    def run_pipeline(self):
        pass
        
        
        
dg = DgSante()

dg.extract_data()



