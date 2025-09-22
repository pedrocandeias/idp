from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: str = "ok"


class UserCreate(BaseModel):
    email: str
    password: str
    org_id: Optional[int] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        # Accept standard emails and special-use domains like .local for demos.
        try:
            from email_validator import validate_email

            info = validate_email(v, check_deliverability=False)
            return info.normalized
        except Exception:
            raise ValueError("Invalid email")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# User
class UserRead(BaseModel):
    id: int
    email: str
    org_id: int | None = None
    roles: list[str] = []

    class Config:
        from_attributes = True


# Organization
class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationRead(OrganizationBase):
    id: int

    class Config:
        from_attributes = True


# Project
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    org_id: int

    class Config:
        from_attributes = True


# Other DTOs (minimal)
class DesignArtifactCreate(BaseModel):
    project_id: int
    name: str
    type: Optional[str] = None
    uri: Optional[str] = None
    meta: Optional[dict] = None


class DesignArtifactRead(DesignArtifactCreate):
    id: int
    object_key: Optional[str] = None
    params_key: Optional[str] = None
    object_mime: Optional[str] = None
    size_bytes: Optional[int] = None
    presigned_url: Optional[str] = None

    class Config:
        from_attributes = True


class AnthropometricDatasetCreate(BaseModel):
    name: str
    source: Optional[str] = None
    schema: Optional[dict] = None
    distributions: Optional[dict] = None


class AnthropometricDatasetRead(AnthropometricDatasetCreate):
    id: int
    org_id: int

    class Config:
        from_attributes = True


class AbilityProfileCreate(BaseModel):
    org_id: int
    name: str
    data: Optional[dict] = None


class AbilityProfileRead(AbilityProfileCreate):
    id: int

    class Config:
        from_attributes = True


class RulePackCreate(BaseModel):
    name: str
    version: str
    rules: Optional[dict] = None


class RulePackRead(RulePackCreate):
    id: int
    org_id: int

    class Config:
        from_attributes = True


class SimulationScenarioCreate(BaseModel):
    project_id: int
    name: str
    config: Optional[dict] = None


class SimulationScenarioRead(SimulationScenarioCreate):
    id: int

    class Config:
        from_attributes = True


class EvaluationRunCreate(BaseModel):
    scenario_id: int
    status: str = "pending"
    metrics: Optional[dict] = None


class EvaluationRunRead(EvaluationRunCreate):
    id: int

    class Config:
        from_attributes = True


class AdaptiveComponentCreate(BaseModel):
    project_id: int
    name: str
    spec: Optional[dict] = None


class AdaptiveComponentRead(AdaptiveComponentCreate):
    id: int

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    project_id: int
    title: str
    content: Optional[dict] = None


class ReportRead(ReportCreate):
    id: int
    html_key: Optional[str] = None
    pdf_key: Optional[str] = None
    checksum_sha256: Optional[str] = None
    presigned_html_url: Optional[str] = None
    presigned_pdf_url: Optional[str] = None

    class Config:
        from_attributes = True
