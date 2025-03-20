# agent.py
from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI

def my_tool(input_text: str) -> str:
    # Esempio di strumento personalizzato: qui puoi integrare una logica specifica
    return f"Output elaborato per: {input_text}"

# Definisci eventuali strumenti da usare
tools = [
    Tool(
        name="MyTool",
        func=my_tool,
        description="Strumento che elabora il testo fornito."
    )
]

# Inizializza il modello LLM (assicurati di avere la chiave API configurata)
llm = ChatOpenAI(temperature=0)

# Inizializza l'agente con il metodo "zero-shot-react-description" (o un altro a tua scelta)
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

def run_agent(query: str) -> str:
    """Esegue la query passando il testo all'agente e restituisce la risposta."""
    return agent.run(query)