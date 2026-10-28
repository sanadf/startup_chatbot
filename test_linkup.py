from dotenv import load_dotenv
from linkup import Client

load_dotenv()

client = Client()

result = client.search(
    query=(
        "Find startups developing AI healthcare software "
        "with a presence in Saudi Arabia. "
        "Identify company names, official websites, "
        "funding stages, and supporting sources."
    ),
    depth="standard",
    output_type="sourcedAnswer",
)

print(result.model_dump_json(indent=2))
