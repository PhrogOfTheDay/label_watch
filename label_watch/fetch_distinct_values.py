import requests

BASE_URL = "https://api.fda.gov/drug/ndc.json"

FIELDS = {
    "route": "openfda.route.exact",
    "dosage_form": "openfda.dosage_form.exact",
    "product_type": "openfda.product_type.exact",
}


def get_distinct_values(field: str) -> list[str]:
    field = f"{field}.exact"
    response = requests.get(
        BASE_URL,
        params={
            "count": field,
            "limit": 1000,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return sorted(item["term"] for item in data["results"])
