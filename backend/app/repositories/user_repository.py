from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.user import User, utc_now


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_clerk_user_id(self, clerk_user_id: str) -> User | None:
        statement = select(User).where(User.clerk_user_id == clerk_user_id)
        return self.session.exec(statement).first()

    def upsert_by_clerk_user_id(
        self,
        user: User,
        *,
        update_existing: bool = False,
    ) -> User:
        existing = self.get_by_clerk_user_id(user.clerk_user_id)
        if existing is not None:
            if update_existing:
                self._copy_mutable_fields(existing, user)
                self.session.add(existing)
                self.session.commit()
                self.session.refresh(existing)
            return existing

        self.session.add(user)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            recovered = self.get_by_clerk_user_id(user.clerk_user_id)
            if recovered is None:
                raise
            if update_existing:
                self._copy_mutable_fields(recovered, user)
                self.session.add(recovered)
                self.session.commit()
                self.session.refresh(recovered)
            return recovered

        self.session.refresh(user)
        return user

    def set_status(self, clerk_user_id: str, status: str) -> User | None:
        user = self.get_by_clerk_user_id(clerk_user_id)
        if user is None:
            return None

        user.status = status
        user.updated_at = utc_now()
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def _copy_mutable_fields(self, target: User, source: User) -> None:
        target.status = source.status
        target.primary_email = source.primary_email
        target.display_name = source.display_name
        target.avatar_url = source.avatar_url
        target.updated_at = utc_now()
