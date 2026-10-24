from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CompanyProfileIn(BaseModel):
    legal_name: str = Field(min_length=1, max_length=255)
    address: str = ""
    phone: str = ""
    website: str = ""
    signatory_name: str = ""
    signatory_title: str = ""
    signature_image: str | None = None


class CompanyProfileOut(ORMModel):
    legal_name: str
    address: str
    phone: str
    website: str
    signatory_name: str
    signatory_title: str
    has_signature: bool
