"""
Tests for APScheduler persistence and job registration.

Verifies:
1. Jobs survive process restart via SQLAlchemy jobstore
2. No duplicate jobs on re-registration
"""
import pytest

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sarthi:sarthi@localhost:5432/sarthi")


@pytest.fixture
def test_scheduler():
    """Create a test scheduler with SQLAlchemy jobstore."""
    scheduler = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL)},
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )
    yield scheduler
    # Cleanup test jobs
    for job in scheduler.get_jobs():
        if "test-tenant" in job.id:
            scheduler.remove_job(job.id)
    if scheduler.running:
        scheduler.shutdown()


def register_test_jobs(scheduler, tenant_id):
    """Register test jobs for a tenant."""
    scheduler.add_job(
        lambda: None,
        trigger=IntervalTrigger(hours=6),
        args=[tenant_id],
        id=f"finance_guardian_{tenant_id}",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: None,
        trigger=CronTrigger(hour=8, minute=0),
        args=[tenant_id],
        id=f"bi_pulse_{tenant_id}",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: None,
        trigger=IntervalTrigger(hours=4),
        args=[tenant_id],
        id=f"ops_watch_{tenant_id}",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: None,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
        args=[tenant_id],
        id=f"investor_update_{tenant_id}",
        replace_existing=True,
    )
    scheduler.add_job(
        lambda: None,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=5),
        args=[tenant_id],
        id=f"weekly_synthesis_{tenant_id}",
        replace_existing=True,
    )


def test_jobs_survive_restart(test_scheduler):
    """APScheduler with SQLAlchemy jobstore must re-load jobs after process restart."""
    scheduler = test_scheduler
    tenant_id = "test-tenant-persist"

    # Register jobs
    if not scheduler.running:
        scheduler.start()

    register_test_jobs(scheduler, tenant_id)
    job_ids_before = {j.id for j in scheduler.get_jobs() if tenant_id in j.id}

    # Verify jobs registered
    assert "finance_guardian_test-tenant-persist" in job_ids_before
    assert "bi_pulse_test-tenant-persist" in job_ids_before
    assert "ops_watch_test-tenant-persist" in job_ids_before
    assert "investor_update_test-tenant-persist" in job_ids_before
    assert "weekly_synthesis_test-tenant-persist" in job_ids_before

    # Simulate restart: shutdown scheduler (jobstore in Postgres persists)
    scheduler.shutdown()

    # Create new scheduler instance using same jobstore
    new_scheduler = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=DATABASE_URL)},
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )
    new_scheduler.start()

    job_ids_after = {j.id for j in new_scheduler.get_jobs() if tenant_id in j.id}

    # Verify jobs survived
    assert "finance_guardian_test-tenant-persist" in job_ids_after
    assert "bi_pulse_test-tenant-persist" in job_ids_after
    assert "ops_watch_test-tenant-persist" in job_ids_after
    assert "investor_update_test-tenant-persist" in job_ids_after
    assert "weekly_synthesis_test-tenant-persist" in job_ids_after
    assert job_ids_before == job_ids_after, "Jobs lost on restart — jobstore not working"

    # Cleanup
    new_scheduler.shutdown()
    for job in scheduler.get_jobs():
        if "test-tenant-persist" in job.id:
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass


def test_no_duplicate_jobs_on_reregister(test_scheduler):
    """Calling register twice must not create duplicates."""
    scheduler = test_scheduler
    tenant_id = "test-tenant-dup"

    if not scheduler.running:
        scheduler.start()

    # Register twice
    register_test_jobs(scheduler, tenant_id)
    register_test_jobs(scheduler, tenant_id)  # second call

    jobs = [j for j in scheduler.get_jobs() if tenant_id in j.id]
    ids = [j.id for j in jobs]

    # Should have exactly one of each job
    expected_jobs = [
        "finance_guardian_test-tenant-dup",
        "bi_pulse_test-tenant-dup",
        "ops_watch_test-tenant-dup",
        "investor_update_test-tenant-dup",
        "weekly_synthesis_test-tenant-dup",
    ]

    for expected in expected_jobs:
        assert ids.count(expected) == 1, f"Duplicate job created: {expected}"

    # Cleanup
    for job in scheduler.get_jobs():
        if tenant_id in job.id:
            try:
                scheduler.remove_job(job.id)
            except Exception:
                pass