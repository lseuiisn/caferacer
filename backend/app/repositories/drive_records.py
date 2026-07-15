from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import CourseNavigationAnchor, CoursePath
from app.models.drive import DriveRecord, DriveRecordAnchorPass, DriveRecordPoint


class DriveRecordRepository:
    def get_owned(self, db: Session, record_id: int, user_id: int) -> DriveRecord | None:
        return db.scalar(
            select(DriveRecord).where(
                DriveRecord.id == record_id,
                DriveRecord.user_id == user_id,
            )
        )

    def last_sequence(self, db: Session, record_id: int) -> int | None:
        return db.scalar(
            select(func.max(DriveRecordPoint.sequence)).where(
                DriveRecordPoint.drive_record_id == record_id
            )
        )

    def list_owned(
        self, db: Session, user_id: int, *, page: int, size: int
    ) -> tuple[list[DriveRecord], int]:
        filters = [DriveRecord.user_id == user_id]
        total = db.scalar(select(func.count()).select_from(DriveRecord).where(*filters)) or 0
        records = list(
            db.scalars(
                select(DriveRecord)
                .where(*filters)
                .order_by(DriveRecord.started_at.desc(), DriveRecord.id.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
        )
        return records, total

    def points(self, db: Session, record_id: int) -> list[DriveRecordPoint]:
        return list(
            db.scalars(
                select(DriveRecordPoint)
                .where(DriveRecordPoint.drive_record_id == record_id)
                .order_by(DriveRecordPoint.sequence)
            )
        )

    def path(self, db: Session, course_id: int) -> list[CoursePath]:
        return list(
            db.scalars(
                select(CoursePath)
                .where(CoursePath.course_id == course_id)
                .order_by(CoursePath.sequence)
            )
        )

    def anchors(self, db: Session, course_id: int) -> list[CourseNavigationAnchor]:
        return list(
            db.scalars(
                select(CourseNavigationAnchor)
                .where(CourseNavigationAnchor.course_id == course_id)
                .order_by(CourseNavigationAnchor.sequence)
            )
        )

    def passed_anchor_ids(self, db: Session, record_id: int) -> set[int]:
        return set(
            db.scalars(
                select(DriveRecordAnchorPass.anchor_id).where(
                    DriveRecordAnchorPass.drive_record_id == record_id
                )
            )
        )
