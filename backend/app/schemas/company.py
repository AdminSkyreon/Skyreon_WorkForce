from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompanyProfileIn(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    address: str = Field(default="", max_length=1000)
    phone: str = Field(default="", max_length=80)
    website: str = Field(default="", max_length=255)
    signatory_name: str = Field(default="", max_length=255)
    signatory_title: str = Field(default="", max_length=120)
    signature_image: str | None = Field(default=None, max_length=2_800_000)


class CompanyProfileOut(ORMModel):
    legal_name: str
    address: str
    phone: str
    website: str
    signatory_name: str
    signatory_title: str
    has_signature: bool
