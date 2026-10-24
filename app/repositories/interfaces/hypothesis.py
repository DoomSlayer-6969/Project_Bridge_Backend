import uuid
from abc import ABC, abstractmethod

from app.models import Hypothesis, HypothesisEvidence


class HypothesisRepository(ABC):
    """Hypotheses and the evidence rows that belong to them."""

    @abstractmethod
    async def get(self, hypothesis_id: uuid.UUID) -> Hypothesis | None: ...

    @abstractmethod
    async def list_for_user(
        self, user_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[Hypothesis]:
        """Newest first."""

    @abstractmethod
    async def add(self, hypothesis: Hypothesis) -> Hypothesis:
        """Persist a new hypothesis and return it with generated fields populated."""

    @abstractmethod
    async def delete(self, hypothesis: Hypothesis) -> None:
        """Delete the hypothesis, its evidence and reflections."""

    @abstractmethod
    async def list_evidence(self, hypothesis_id: uuid.UUID) -> list[HypothesisEvidence]: ...

    @abstractmethod
    async def add_evidence(self, evidence: HypothesisEvidence) -> HypothesisEvidence:
        """Persist a new evidence row and return it with generated fields populated."""
