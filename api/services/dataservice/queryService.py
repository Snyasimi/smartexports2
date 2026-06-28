import os
import re

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

load_dotenv()



def clean_llm_response(text: str) -> str:
    if not text:
        return ""

    # Remove every <think>...</think> block
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return text.strip()



class QueryService:

    def __init__(self):
        """
        Initialize the Neo4j connection and Featherless AI client.
        """

        # -----------------------------
        # Neo4j
        # -----------------------------
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USERNAME"),
                os.getenv("NEO4J_PASSWORD"),
            ),
        )

        # -----------------------------
        # Featherless AI
        # -----------------------------
        self.client = OpenAI(
            api_key=os.getenv("FEATHERLESS_API_KEY"),
            base_url="https://api.featherless.ai/v1",
        )

        # -----------------------------
        # Model
        # Change this whenever you want
        # -----------------------------
        #self.model = "Qwen/Qwen3-32B"
        self.model="Qwen/Qwen3-14B"

        # -----------------------------
        # Shared system prompt
        # -----------------------------
        self.system_prompt = """
You are an agricultural pesticide assistant.

Your job is to answer questions using ONLY the Neo4j database results provided.

Never invent information.

If the database contains no matching records,
clearly say that no information was found.

Keep responses concise and easy to understand.
"""

    def isActiveSubstanceBanned(self, substance_name: str) -> str:
        """
        Checks whether an active substance is banned.
        If it is approved, the function also retrieves all available MRLs.
        The LLM generates the final response from the Neo4j results.
        """

        cypher = """
            MATCH (c:Chemical)
            WHERE toLower(c.active_substance) CONTAINS toLower($name)

        OPTIONAL MATCH (c)-[:HAS_RESIDUE]->(r:Residue)
        OPTIONAL MATCH (r)-[:HAS_MRL_LEVEL]->(m:MRL)
        OPTIONAL MATCH (m)-[:FOR_PRODUCT]->(p:Product)

        RETURN
            c.active_substance AS substance,
            c.status AS status,
            collect(
                DISTINCT {
                    residue: r.residue_name,
                    product: p.product_name,
                    mrl: m.mrl_value,
                    unit: m.unit
                }
            ) AS mrls
        """

        with self.driver.session() as session:
            record = session.run(cypher, name=substance_name).single()

        if record is None:
            return f"I couldn't find an active substance called '{substance_name}'."

        data = record.data()

        prompt = f"""
    You are an agricultural pesticide expert.

    Below is information retrieved directly from a Neo4j knowledge graph.

    Substance:
    {data['substance']}

    Status:
    {data['status']}

    Maximum Residue Levels:
{   data['mrls']}

    Instructions:
    1. Use ONLY this information.
    2. If the status says "Not approved", "Banned", or anything similar, clearly state that the substance is banned or not approved.
    3. Otherwise, state that the substance is approved.
    4. If MRLs exist, summarize them in a readable way.
    5. If no MRLs exist, mention that no MRL information is available.
    6. Do not invent any information.
    7. Keep the response concise and professional.
    
    """

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                "role": "system",
                "content": "You answer questions using only information supplied from a Neo4j knowledge graph."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=300,
    )

        #return response.choices[0].message.content.strip()
        response = clean_llm_response(response.choices[0].message.content.strip())
        return response





if __name__ == "__main__":

    # Create the service
    service = QueryService()

    # Test substance
    substance = "Methidathion"      # Change this to any active substance

    print(f"Searching for: {substance}")
    print("-" * 80)

    try:
        response = service.isActiveSubstanceBanned(substance)
        print(response)

    except Exception as e:
        print("An error occurred:")
        print(e)

    finally:
        del service






















def getActiveSubstanceMRL():
    pass

def getActiveSubstanceResidue():
    pass

def getProductActiveSubstanceMRL():
    pass

def getProductResidues():
    pass

def getProductResidueMRL():
    pass

def isActiveSubstanceBanned():
    
    pass





class queryService:
    pass
