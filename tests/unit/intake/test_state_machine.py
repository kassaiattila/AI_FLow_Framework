"""IntakePackage + IntakeFile state machine tests.

Source: 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md Sections 1-2
"""

import pytest

from aiflow.intake.exceptions import InvalidStateTransitionError
from aiflow.intake.package import (
    IntakeFile,
    IntakePackage,
    IntakePackageStatus,
    IntakeSourceType,
)
from aiflow.intake.state_machine import (
    PACKAGE_SM,
    IntakeFileStatus,
    TransitionRecord,
    is_terminal_status,
    validate_file_transition,
    validate_package_transition,
)


def _make_package(status: IntakePackageStatus = IntakePackageStatus.RECEIVED) -> IntakePackage:
    return IntakePackage(
        source_type=IntakeSourceType.EMAIL,
        tenant_id="test_tenant",
        status=status,
        files=[
            IntakeFile(
                file_path="/tmp/test.pdf",
                file_name="test.pdf",
                mime_type="application/pdf",
                size_bytes=1024,
                sha256="a" * 64,
            )
        ],
    )


class TestPackageHappyPath:
    def test_full_happy_path_transitions(self):
        chain = [
            (IntakePackageStatus.RECEIVED, IntakePackageStatus.NORMALIZED),
            (IntakePackageStatus.NORMALIZED, IntakePackageStatus.ROUTED),
            (IntakePackageStatus.ROUTED, IntakePackageStatus.PARSED),
            (IntakePackageStatus.PARSED, IntakePackageStatus.CLASSIFIED),
            (IntakePackageStatus.CLASSIFIED, IntakePackageStatus.EXTRACTED),
            (IntakePackageStatus.EXTRACTED, IntakePackageStatus.ARCHIVED),
        ]
        for from_s, to_s in chain:
            validate_package_transition(from_s, to_s)

    def test_review_branch_path(self):
        validate_package_transition(
            IntakePackageStatus.EXTRACTED, IntakePackageStatus.REVIEW_PENDING
        )
        validate_package_transition(
            IntakePackageStatus.REVIEW_PENDING, IntakePackageStatus.REVIEWED
        )
        validate_package_transition(IntakePackageStatus.REVIEWED, IntakePackageStatus.ARCHIVED)

    def test_classified_to_review_pending(self):
        validate_package_transition(
            IntakePackageStatus.CLASSIFIED, IntakePackageStatus.REVIEW_PENDING
        )


class TestPackageInvalidTransitions:
    def test_skip_states_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(IntakePackageStatus.RECEIVED, IntakePackageStatus.EXTRACTED)

    def test_received_to_archived_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(IntakePackageStatus.RECEIVED, IntakePackageStatus.ARCHIVED)

    def test_backward_transition_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(IntakePackageStatus.PARSED, IntakePackageStatus.RECEIVED)


class TestPackageTerminalStates:
    def test_archived_no_further_transitions(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(IntakePackageStatus.ARCHIVED, IntakePackageStatus.EXTRACTED)

    def test_quarantined_no_further_transitions(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(
                IntakePackageStatus.QUARANTINED, IntakePackageStatus.RECEIVED
            )

    def test_archived_is_terminal(self):
        assert is_terminal_status(IntakePackageStatus.ARCHIVED) is True

    def test_quarantined_is_terminal(self):
        assert is_terminal_status(IntakePackageStatus.QUARANTINED) is True

    def test_received_is_not_terminal(self):
        assert is_terminal_status(IntakePackageStatus.RECEIVED) is False

    def test_failed_is_not_terminal(self):
        assert is_terminal_status(IntakePackageStatus.FAILED) is False


class TestPackageFailedAndResume:
    def test_any_non_terminal_to_failed(self):
        non_terminal = [
            IntakePackageStatus.RECEIVED,
            IntakePackageStatus.NORMALIZED,
            IntakePackageStatus.ROUTED,
            IntakePackageStatus.PARSED,
            IntakePackageStatus.CLASSIFIED,
            IntakePackageStatus.EXTRACTED,
            IntakePackageStatus.REVIEW_PENDING,
            IntakePackageStatus.REVIEWED,
        ]
        for status in non_terminal:
            validate_package_transition(status, IntakePackageStatus.FAILED)

    def test_failed_resume_to_received(self):
        validate_package_transition(IntakePackageStatus.FAILED, IntakePackageStatus.RECEIVED)

    def test_failed_resume_to_normalized(self):
        validate_package_transition(IntakePackageStatus.FAILED, IntakePackageStatus.NORMALIZED)

    def test_failed_cannot_skip_to_extracted(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_package_transition(IntakePackageStatus.FAILED, IntakePackageStatus.EXTRACTED)


class TestPackageReviewBranch:
    def test_reviewed_can_re_extract(self):
        validate_package_transition(IntakePackageStatus.REVIEWED, IntakePackageStatus.EXTRACTED)

    def test_reviewed_can_archive(self):
        validate_package_transition(IntakePackageStatus.REVIEWED, IntakePackageStatus.ARCHIVED)

    def test_reviewed_can_fail(self):
        validate_package_transition(IntakePackageStatus.REVIEWED, IntakePackageStatus.FAILED)


class TestStateMachineApply:
    def test_apply_valid_transition(self):
        pkg = _make_package()
        record = PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED, actor_id="normalizer")
        assert pkg.status == IntakePackageStatus.NORMALIZED
        assert isinstance(record, TransitionRecord)
        assert record.from_status == "received"
        assert record.to_status == "normalized"
        assert record.actor_id == "normalizer"

    def test_apply_idempotent_noop(self):
        pkg = _make_package(status=IntakePackageStatus.NORMALIZED)
        result = PACKAGE_SM.apply(pkg, IntakePackageStatus.NORMALIZED)
        assert result is None
        assert pkg.status == IntakePackageStatus.NORMALIZED

    def test_apply_invalid_transition_raises(self):
        pkg = _make_package()
        with pytest.raises(InvalidStateTransitionError):
            PACKAGE_SM.apply(pkg, IntakePackageStatus.ARCHIVED)

    def test_apply_full_chain(self):
        pkg = _make_package()
        records = []
        chain = [
            IntakePackageStatus.NORMALIZED,
            IntakePackageStatus.ROUTED,
            IntakePackageStatus.PARSED,
            IntakePackageStatus.CLASSIFIED,
            IntakePackageStatus.EXTRACTED,
            IntakePackageStatus.ARCHIVED,
        ]
        for target in chain:
            r = PACKAGE_SM.apply(pkg, target)
            assert r is not None
            records.append(r)
        assert pkg.status == IntakePackageStatus.ARCHIVED
        assert len(records) == 6


class TestStateMachineResume:
    def test_resume_from_failed(self):
        pkg = _make_package(status=IntakePackageStatus.FAILED)
        record = PACKAGE_SM.resume_from_checkpoint(pkg, IntakePackageStatus.RECEIVED)
        assert pkg.status == IntakePackageStatus.RECEIVED
        assert record is not None
        assert record.actor_id == "admin"

    def test_resume_from_non_failed_raises(self):
        pkg = _make_package(status=IntakePackageStatus.PARSED)
        with pytest.raises(InvalidStateTransitionError, match="FAILED"):
            PACKAGE_SM.resume_from_checkpoint(pkg, IntakePackageStatus.RECEIVED)


class TestStateMachineHelpers:
    def test_get_allowed_from_received(self):
        allowed = PACKAGE_SM.get_allowed(IntakePackageStatus.RECEIVED)
        assert IntakePackageStatus.NORMALIZED in allowed
        assert IntakePackageStatus.FAILED in allowed
        assert len(allowed) == 2

    def test_get_allowed_from_terminal(self):
        allowed = PACKAGE_SM.get_allowed(IntakePackageStatus.ARCHIVED)
        assert len(allowed) == 0

    def test_get_resumable_targets(self):
        targets = PACKAGE_SM.get_resumable_targets()
        assert IntakePackageStatus.RECEIVED in targets
        assert IntakePackageStatus.NORMALIZED in targets


class TestFileStateMachine:
    def test_file_happy_path(self):
        chain = [
            (IntakeFileStatus.PENDING, IntakeFileStatus.ROUTED),
            (IntakeFileStatus.ROUTED, IntakeFileStatus.PARSED),
            (IntakeFileStatus.PARSED, IntakeFileStatus.CLASSIFIED),
            (IntakeFileStatus.CLASSIFIED, IntakeFileStatus.EXTRACTED),
            (IntakeFileStatus.EXTRACTED, IntakeFileStatus.ARCHIVED),
        ]
        for from_s, to_s in chain:
            validate_file_transition(from_s, to_s)

    def test_file_skip_raises(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_file_transition(IntakeFileStatus.PENDING, IntakeFileStatus.ARCHIVED)

    def test_file_any_to_failed(self):
        for status in [
            IntakeFileStatus.PENDING,
            IntakeFileStatus.ROUTED,
            IntakeFileStatus.PARSED,
            IntakeFileStatus.CLASSIFIED,
            IntakeFileStatus.EXTRACTED,
        ]:
            validate_file_transition(status, IntakeFileStatus.FAILED)

    def test_file_failed_retry_to_pending(self):
        validate_file_transition(IntakeFileStatus.FAILED, IntakeFileStatus.PENDING)

    def test_file_archived_is_terminal(self):
        assert is_terminal_status(IntakeFileStatus.ARCHIVED) is True

    def test_file_pending_is_not_terminal(self):
        assert is_terminal_status(IntakeFileStatus.PENDING) is False

    def test_file_archived_no_further(self):
        with pytest.raises(InvalidStateTransitionError):
            validate_file_transition(IntakeFileStatus.ARCHIVED, IntakeFileStatus.PENDING)


class TestTransitionRecord:
    def test_record_fields(self):
        record = TransitionRecord(
            from_status="received",
            to_status="normalized",
            actor_id="test_user",
            metadata={"reason": "auto"},
        )
        assert record.from_status == "received"
        assert record.to_status == "normalized"
        assert record.actor_id == "test_user"
        assert record.timestamp is not None
        assert record.metadata == {"reason": "auto"}

    def test_record_default_actor(self):
        record = TransitionRecord(from_status="a", to_status="b")
        assert record.actor_id == "system"
