from typing import Annotated

from InquirerPy import inquirer
import pandas as pd
import questionary
import typer

from label_watch.fetch import fetch_from_ndc, fetch_records_json
from label_watch.fetch_distinct_values import get_distinct_values

app = typer.Typer(no_args_is_help=True)
typer.echo("Welcome to LabelWatch")


@app.command()
def start():
    """
    START
    """
    typer.echo("Welcome to LabelWatch")


@app.command()
def check_for_updates():
    """
    Check if any of the labels you have already selected have been updated. If so, you will be notified and snapshots will be created for the updated labels. If not, you will be informed that there are no updates available.
    """
    typer.echo("Checking for updates...")

    typer.echo("No updates available.")


@app.command()
def select_labels():
    """
    Use this function to select the set id you want to monitor by searching by drug name and company name
    """
    selected = questionary.select(
        "How do you want to search for the drug of your interest ?",
        choices=["Brand Name", "Generic Drug Name"],
    ).ask()

    selected_drug, selected_generic_drug = None, None
    if selected == "Brand Name":
        brand_names = [
            x["term"] for x in fetch_records_json(count="openfda.brand_name.exact")["results"]
        ]
        selected_drug = inquirer.fuzzy(
            message="Search for a drug by its brand name: ", choices=brand_names
        ).execute()

    else:
        generic_drug_names = [
            x["term"] for x in fetch_records_json(count="openfda.generic_name.exact")["results"]
        ]
        selected_generic_drug = inquirer.fuzzy(
            message="Search for a drug by its generic name:", choices=generic_drug_names
        ).execute()
        company_names = [
            x["term"]
            for x in fetch_records_json(
                count="openfda.manufacturer_name.exact", drug_name=selected_generic_drug
            )["results"]
        ]
    company_names = [
        x["term"]
        for x in fetch_records_json(
            count="openfda.manufacturer_name.exact",
            brand_name=selected_drug,
            drug_name=selected_generic_drug,
        )["results"]
    ]
    selected_company_name = inquirer.fuzzy(
        message="Select a manufacturer:", choices=company_names
    ).execute()

    select_labels_phase2(
        selected_company=selected_company_name,
        selected_drug=selected_drug,
        selected_generic_drug=selected_generic_drug,
    )


def select_labels_phase2(
    selected_company: str,
    selected_drug: str | None = None,
    selected_generic_drug: str | None = None,
):
    returned_records = [
        x
        for x in fetch_records_json(
            manufacturer=selected_company,
            brand_name=selected_drug,
            drug_name=selected_generic_drug,
        )["results"]
    ]
    if len(returned_records) == 1:
        typer.echo(
            "Only one set id matching your query was found, moving to automatically add it to tracked set ids"
        )
        return
    product_ndcs = [x["openfda"]["product_ndc"][0] for x in returned_records]

    available_dosage_forms = [
        x["term"] for x in fetch_from_ndc(product_ndcs, count="dosage_form")["results"]
    ]
    if len(available_dosage_forms) != 1:
        selected_dosage_form = inquirer.fuzzy(
            message="Select the dosage form you want to monitor",
            choices=available_dosage_forms + ["All"],
        ).execute()
        if selected_dosage_form != "All":
            returned_records = [
                x
                for x in returned_records
                if x["openfda"]["product_ndc"][0] in selected_dosage_form
            ]

    rows = []

    for record in returned_records["results"]:
        openfda = record.get("openfda", {})

        rows.append(
            {
                "set_id": record.get("set_id"),
                "id": record.get("id"),
                "version": record.get("version"),
                "effective_time": record.get("effective_time"),
                "brand_name": openfda.get("brand_name", []),
                "manufacturer": openfda.get("manufacturer_name", []),
                "generic_name": openfda.get("generic_name", []),
                "product_ndc": openfda.get("product_ndc", []),
                "package_ndc": openfda.get("package_ndc", []),
                "dosage_form": openfda.get("dosage_form", []),
                "route": openfda.get("route", []),
                "product_type": openfda.get("product_type", []),
            }
        )

    df = pd.DataFrame(rows)
    print(df)


@app.command(name="add_labels")
def add_labels_to_monitor(
    set_label: Annotated[str, "The set label you want the monitoring to be done on"],
):
    """
    Directly add new labels to add to your monitoring list
    If you are unsure about the set label of the drug report you want to monitor use the command select_labels instead
    """


if __name__ == "__main__":
    select_labels()
