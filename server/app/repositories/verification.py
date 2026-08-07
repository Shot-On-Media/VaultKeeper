from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.verification import VerificationReport


class VerificationReportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[VerificationReport]:
        return list(
            self.session.scalars(
                select(VerificationReport).order_by(
                    VerificationReport.created_at.desc()
                )
            )
        )

    def add(self, report: VerificationReport) -> VerificationReport:
        self.session.add(report)
        self.session.flush()
        self.session.refresh(report)
        return report
