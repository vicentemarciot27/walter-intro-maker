import requests
import os
import json
from pathlib import Path

def get_list_name_from_slug(list_slug:str):
    lists_json = json.load(open(Path(__file__).parent / "lists.json"))
    for list in lists_json["data"]:
        if list["api_slug"] == list_slug:
            return list["name"]
    raise ValueError(f"List slug {list_slug} not found")

ATTIO_API_KEY = os.getenv("ATTIO_API_KEY")
PATH_TO_LISTS_JSON = Path("./lists.json")

def list_record_entries(record_id: str, object: str):
    url = f"https://api.attio.com/v2/objects/{object}/records/{record_id}/entries"

    headers = {
        "Authorization": f"Bearer {ATTIO_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers).json()["data"]
    except Exception as e:
        raise RuntimeError(f"Erro ao buscar entradas do registro: {e}")

    for list in response:
        list["name"] = get_list_name_from_slug(list["list_api_slug"])
        # remove created_at field
        list.pop("created_at", None)
        list.pop("list_id", None)

    return response


if __name__ == "__main__":
    print(list_record_entries("00010e3d-74b6-4471-90c3-ba6a637f901f", "companies"))
