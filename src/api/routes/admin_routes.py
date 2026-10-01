"""Network & coverage admin endpoints (ADMIN only) and the public-to-any-user network list."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.deps import AdminUser, AnyUser, AppClock, DbConn
from src.api.schemas import CoverageRuleCreate, HospitalCreate, HospitalPatch, ProductCreate
from src.domain.coverage_rules import CoverageRule, CoverageRuleVersion
from src.domain.money import money_str
from src.service import admin_service

router = APIRouter(prefix="/api", tags=["admin"])


def _version_view(v: CoverageRuleVersion) -> dict[str, object]:
    r = v.rule
    return {
        "product_code": v.product_code, "version": v.version, "published_by": v.published_by,
        "published_at": v.published_at, "auto_approve_threshold": money_str(r.auto_approve_threshold),
        "auto_approved_diagnoses": list(r.auto_approved_diagnoses), "excluded_diagnoses": list(r.excluded_diagnoses),
        "per_claim_cap": money_str(r.per_claim_cap), "buffer_pct": str(r.buffer_pct),
        "deductible": money_str(r.deductible), "copay_pct": str(r.copay_pct), "reason_codes": list(r.reason_codes),
    }


@router.get("/network-hospitals")
def network_hospitals(conn: DbConn, principal: AnyUser) -> list[dict[str, object]]:
    return admin_service.network_hospitals(conn)


@router.get("/admin/hospitals")
def list_hospitals(conn: DbConn, principal: AdminUser) -> list[dict[str, object]]:
    return admin_service.list_hospitals(conn)


@router.post("/admin/hospitals", status_code=status.HTTP_201_CREATED)
def create_hospital(
    body: HospitalCreate, conn: DbConn, clock: AppClock, principal: AdminUser
) -> dict[str, object]:
    return admin_service.create_hospital(
        conn, code=body.code, name=body.name, city=body.city, in_network=body.in_network, clock=clock
    )


@router.patch("/admin/hospitals/{code}")
def patch_hospital(code: str, body: HospitalPatch, conn: DbConn, principal: AdminUser) -> dict[str, object]:
    return admin_service.set_network_status(conn, code, body.in_network)


@router.get("/admin/products")
def list_products(conn: DbConn, principal: AdminUser) -> list[dict[str, object]]:
    return admin_service.list_products(conn)


@router.post("/admin/products", status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate, conn: DbConn, clock: AppClock, principal: AdminUser
) -> dict[str, object]:
    return admin_service.create_product(
        conn, code=body.code, name=body.name, sum_insured=money_str(body.sum_insured),
        annual_premium=money_str(body.annual_premium), clock=clock,
    )


@router.get("/admin/products/{code}/coverage-rules")
def list_rules(code: str, conn: DbConn, principal: AdminUser) -> list[dict[str, object]]:
    return [_version_view(v) for v in admin_service.list_rule_versions(conn, code)]


@router.post("/admin/products/{code}/coverage-rules", status_code=status.HTTP_201_CREATED)
def publish_rule(
    code: str, body: CoverageRuleCreate, conn: DbConn, clock: AppClock, principal: AdminUser
) -> dict[str, object]:
    rule = CoverageRule(
        auto_approve_threshold=body.auto_approve_threshold,
        auto_approved_diagnoses=tuple(body.auto_approved_diagnoses),
        excluded_diagnoses=tuple(body.excluded_diagnoses),
        per_claim_cap=body.per_claim_cap, buffer_pct=body.buffer_pct, deductible=body.deductible,
        copay_pct=body.copay_pct, reason_codes=tuple(body.reason_codes),
    )
    return _version_view(admin_service.publish_rule(conn, principal, code, rule, clock))
