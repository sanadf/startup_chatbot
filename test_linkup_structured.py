
from dotenv import load_dotenv
from linkup import Client
import json

load_dotenv()

client = Client()

startup_schema = {
    "type": "object",
    "properties": {
        "companies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "website": {"type": "string"},
                    "description": {"type": "string"},
                    "funding_stage": {"type": "string"},
                    "source_url": {"type": "string"},
                },
                "required": [
                    "name",
                    "website",
                    "description",
                    "funding_stage",
                    "source_url",
                ],
            },
        }
    },
    "required": ["companies"],
}

result = client.search(
    query=(
        "Find up to 5 real AI healthcare startups "
        "operating in Saudi Arabia. "
        "Only include identifiable companies, not "
        "individual software products. "
        "Provide their official website, description, "
        "funding stage, and a supporting source URL. "
        "Use 'Not publicly verified' when information "
        "cannot be confirmed. Do not invent facts."
    ),
    depth="standard",
    output_type="structured",
    structured_output_schema=startup_schema,
)

data = (
    result.model_dump()
    if hasattr(result, "model_dump")
    else result
)

print(json.dumps(data, indent=2, ensure_ascii=False))
