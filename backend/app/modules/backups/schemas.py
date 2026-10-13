"""Backup requests never allow arbitrary paths, commands or live restore targets."""

from typing import Literal

from pydantic import BaseModel, SecretStr

from app.modules.backups.models import BackupRecord


class BackupRequest(BaseModel):
    passphrase: SecretStr
    confirmation: Literal["BACKUP ALL"]


class RecoveryRequest(BaseModel):
    passphrase: SecretStr
    confirmation: Literal["VERIFY", "ISOLATED DRILL"]


class BackupCatalogue(BaseModel):
    items: list[BackupRecord]
    directory: str
    drill_enabled: bool
    scope: str = "Toàn bộ bản cài đặt, gồm tất cả tenant và khóa ModelOps đã mã hóa"
