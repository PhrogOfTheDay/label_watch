from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OpenFDAMetadataResults(BaseModel):
    skip: int | None = None
    limit: int | None = None
    total: int | None = None


class OpenFDAMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    disclaimer: str | None = None
    terms: str | None = None
    license: str | None = None
    last_updated: str | None = None
    results: OpenFDAMetadataResults | None = None


class OpenFDA(BaseModel):
    model_config = ConfigDict(extra="allow")

    application_number: list[str] | None = None
    brand_name: list[str] | None = None
    generic_name: list[str] | None = None
    manufacturer_name: list[str] | None = None

    product_ndc: list[str] | None = None
    package_ndc: list[str] | None = None
    product_type: list[str] | None = None
    route: list[str] | None = None
    substance_name: list[str] | None = None
    dosage_form: list[str] | None = None

    rxcui: list[str] | None = None
    spl_id: list[str] | None = None
    spl_set_id: list[str] | None = None
    unii: list[str] | None = None
    upc: list[str] | None = None

    is_original_packager: list[bool] | None = None
    original_packager_product_ndc: list[str] | None = None

    pharm_class_moa: list[str] | None = None
    pharm_class_epc: list[str] | None = None
    pharm_class_cs: list[str] | None = None
    pharm_class_pe: list[str] | None = None
    nui: list[str] | None = None


class DrugLabel(BaseModel):
    model_config = ConfigDict(extra="allow")

    set_id: str | None = None
    id: str | None = None
    effective_time: str | None = None
    version: str | None = None

    openfda: OpenFDA | None = None
    boxed_warning: list[str] | None = None
    warnings: list[str] | None = None
    warnings_and_cautions: list[str] | None = None
    contraindications: list[str] | None = None
    precautions: list[str] | None = None
    general_precautions: list[str] | None = None
    other_safety_information: list[str] | None = None
    recent_major_changes: list[str] | None = None
    risks: list[str] | None = None
    adverse_reactions: list[str] | None = None
    drug_interactions: list[str] | None = None
    drug_and_or_laboratory_test_interactions: list[str] | None = None
    laboratory_tests: list[str] | None = None
    overdosage: list[str] | None = None
    use_in_specific_populations: list[str] | None = None
    pregnancy: list[str] | None = None
    pregnancy_or_breast_feeding: list[str] | None = None
    nursing_mothers: list[str] | None = None
    labor_and_delivery: list[str] | None = None
    pediatric_use: list[str] | None = None
    geriatric_use: list[str] | None = None
    teratogenic_effects: list[str] | None = None
    nonteratogenic_effects: list[str] | None = None
    do_not_use: list[str] | None = None
    ask_doctor: list[str] | None = None
    ask_doctor_or_pharmacist: list[str] | None = None
    stop_use: list[str] | None = None
    when_using: list[str] | None = None
    keep_out_of_reach_of_children: list[str] | None = None
    environmental_warning: list[str] | None = None
    indications_and_usage: list[str] | None = None
    dosage_and_administration: list[str] | None = None
    dosage_forms_and_strengths: list[str] | None = None
    active_ingredient: list[str] | None = None
    inactive_ingredient: list[str] | None = None
    purpose: list[str] | None = None
    route: list[str] | None = None
    instructions_for_use: list[str] | None = None
    clinical_pharmacology: list[str] | None = None
    clinical_studies: list[str] | None = None
    mechanism_of_action: list[str] | None = None
    pharmacodynamics: list[str] | None = None
    pharmacokinetics: list[str] | None = None
    pharmacogenomics: list[str] | None = None
    nonclinical_toxicology: list[str] | None = None
    carcinogenesis_and_mutagenesis_and_impairment_of_fertility: list[str] | None = None
    microbiology: list[str] | None = None
    description: list[str] | None = None
    references: list[str] | None = None
    drug_abuse_and_dependence: list[str] | None = None
    controlled_substance: list[str] | None = None
    abuse: list[str] | None = None
    dependence: list[str] | None = None
    information_for_patients: list[str] | None = None
    patient_medication_information: list[str] | None = None
    spl_medguide: list[str] | None = None
    spl_patient_package_insert: list[str] | None = None
    health_care_provider_letter: list[str] | None = None
    questions: list[str] | None = None
    how_supplied: list[str] | None = None
    storage_and_handling: list[str] | None = None
    disposal_and_waste_handling: list[str] | None = None
    package_label_principal_display_panel: list[str] | None = None
    statement_of_identity: list[str] | None = None
    animal_pharmacology_and_or_toxicology: list[str] | None = None
    residue_warning: list[str] | None = None
    food_safety_warning: list[str] | None = None
    guaranteed_analysis_of_feed: list[str] | None = None
    information_for_owners_or_caregivers: list[str] | None = None
    user_safety_warnings: list[str] | None = None
    safe_handling_warning: list[str] | None = None
    health_claim: list[str] | None = None
    accessories: list[str] | None = None
    alarms: list[str] | None = None
    assembly_or_installation_instructions: list[str] | None = None
    calibration_instructions: list[str] | None = None
    cleaning: list[str] | None = None
    compatible_accessories: list[str] | None = None
    components: list[str] | None = None
    diagram_of_device: list[str] | None = None
    intended_use_of_the_device: list[str] | None = None
    troubleshooting: list[str] | None = None
    spl_product_data_elements: list[str] | None = None
    spl_indexing_data_elements: list[str] | None = None
    spl_unclassified_section: list[str] | None = None


class OpenFDAResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    meta: OpenFDAMetadata
    results: list[DrugLabel]
