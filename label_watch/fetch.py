from models.label_class import DrugLabel, OpenFDAResponse
from models.url_param_class import URL_Params
import requests
from label_watch.util import createTypeAdapter


def fetch_records(
    brand_name: str | None = None,
    drug_name: str | None = None,
    set_id: str | None = None,
    id: str | None = None,
    manufacturer: str | None = None,
    other_params: list[URL_Params] | None = None,
    timeout: int | None = 20,
    count: int | None = None,
    limit: int | None = 1000,
) -> OpenFDAResponse:

    params = {}
    if limit:
        params.update({"limit": limit})
    if count:
        params.update({"count": count})

    url = "https://api.fda.gov/drug/label.json?search="
    if brand_name:
        url += f"AND openfda.brand_name:'{brand_name}' "
    if set_id:
        url += f"AND set_id:'{set_id}' "
    if id:
        url += f"AND id:'{id}' "
    if drug_name:
        url += f"AND openfda.generic_name:'{drug_name}' "

    if manufacturer:
        url += f"AND openfda.manufacturer_name:'{manufacturer}' "

    for param in other_params or []:
        if param.condition:
            condition_str = f" {param.condition[0]} ".join(param.condition)
            url += f" {condition_str} {param.search}:'{param.value}' "
        else:
            url += f" {condition_str} {param.search}:'{param.value}'"

    response = requests.get(url, params=params, timeout=timeout)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch records: {response.status_code} - {response.text}")

    type_adapter = createTypeAdapter(OpenFDAResponse)

    json_data = response.json()

    parsed_response = OpenFDAResponse.model_validate(json_data)

    validated_response: list[DrugLabel] = parsed_response.results

    return validated_response


def fetch_records_json(
    brand_name: str | None = None,
    drug_name: str | None = None,
    set_id: str | None = None,
    id: str | None = None,
    manufacturer: str | None = None,
    other_params: list[URL_Params] | None = None,
    timeout: int = 20,
    count: str | None = None,
    limit: int | None = 1000,
) -> dict:

    base_url = "https://api.fda.gov/drug/label.json"

    conditions = []

    standard_filters = {
        "openfda.brand_name": brand_name,
        "openfda.generic_name": drug_name,
        "set_id": set_id,
        "id": id,
        "openfda.manufacturer_name": manufacturer,
    }

    for field, value in standard_filters.items():
        if value is not None:
            conditions.append(f'{field}:"{value}"')

    search_expression = " AND ".join(conditions)

    for param in other_params or []:
        expression = f'{param.search}:"{param.value}"'

        if search_expression:
            search_expression += f" {param.condition} {expression}"
        else:
            search_expression = expression

    params = {}

    if search_expression:
        params["search"] = search_expression

    if count is not None:
        params["count"] = count

    if limit is not None:
        params["limit"] = limit

    response = requests.get(
        base_url,
        params=params,
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()


def fetch_from_ndc(
    ndcs=list[str],
    other_params: list[URL_Params] | None = None,
    timeout: int = 20,
    count: str | None = None,
    limit: int | None = 1000,
):
    base_url = "https://api.fda.gov/drug/ndc.json?search=product_ndc:"
    params = {}

    ndc_params = "("
    for index, x in enumerate(ndcs):
        ndc_params += f'"{x}"'
        if index != len(ndcs) - 1:
            ndc_params += " OR "
        else:
            ndc_params += ")"
    base_url += ndc_params

    if count is not None:
        params["count"] = f"{count}.exact"

    if limit is not None:
        params["limit"] = limit

    if other_params:
        for param in other_params:
            if param.condition:
                condition_str = f" {param.condition[0]} ".join(param.condition)
                params[param.search] = f'{condition_str} {param.search}:"{param.value}"'
            else:
                params[param.search] = f'{param.search}:"{param.value}"'

    response = requests.get(
        base_url,
        params=params,
        timeout=timeout,
    )

    response.raise_for_status()

    return response.json()
