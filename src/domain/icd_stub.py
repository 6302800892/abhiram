"""Static ICD-10 stub (brief 6.3: no real ICD master). The only diagnosis catalogue in MediCard."""

from __future__ import annotations

ICD_STUB: dict[str, str] = {
    "K35.8": "Acute appendicitis",
    "J18.9": "Pneumonia, unspecified",
    "O80": "Normal delivery",
    "S52.5": "Fracture of lower end of radius",
    "I21.9": "Acute myocardial infarction",
    "N20.0": "Calculus of kidney",
    "H25.9": "Age-related cataract",
    "M17.1": "Primary osteoarthritis of knee",
    "C50.9": "Malignant neoplasm of breast",
    "E11.9": "Type 2 diabetes mellitus",
    "Z41.1": "Cosmetic surgery",
    "F10.2": "Alcohol dependence",
}

PROCEDURE_STUB: dict[str, str] = {
    "0DTJ4ZZ": "Laparoscopic appendectomy",
    "0QSJ04Z": "Fixation of radius fracture",
    "02703ZZ": "Coronary angioplasty",
    "08RJ3JZ": "Cataract lens replacement",
    "0SRD0J9": "Knee replacement",
    "10E0XZZ": "Delivery of products of conception",
    "GEN-CONSULT": "Specialist consultation",
    "GEN-ICU": "ICU stay per day",
}


def is_known_diagnosis(code: str) -> bool:
    return code in ICD_STUB


def diagnosis_label(code: str) -> str:
    return ICD_STUB.get(code, "Unknown diagnosis")
