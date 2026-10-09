from pathlib import Path

p = Path("tests/test_jobs.py")
content = p.read_text(encoding="utf-8")

new_tests = """

@pytest.mark.asyncio
async def test_delete_running_job_rejected_409():
    \"\"\"Deleting a non-terminal (running/queued) job must be rejected with 409.\"\"\"
    for active_status in ("queued", "running"):
        job = SimpleNamespace(id=f"job_{active_status}", status=active_status)
        session = _fresh_session()
        session.execute = AsyncMock(return_value=_execute_result(scalar=job))
        with pytest.raises(AppException) as exc_info:
            await jobs_service.delete_job(session, job.id)
        assert exc_info.value.status_code == 409
        assert exc_info.value.code == "job_not_terminal"


@pytest.mark.asyncio
async def test_cleanup_jobs_invalid_status_rejected_400():
    \"\"\"Cleanup with non-terminal status (e.g. running) must be rejected with 400.\"\"\"
    session = _fresh_session()
    with pytest.raises(AppException) as exc_info:
        await jobs_service.cleanup_jobs(session, statuses=["completed", "running"])
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_CLEANUP_STATUS"
"""

if "test_delete_running_job_rejected_409" not in content:
    content = content.rstrip() + new_tests
    p.write_text(content, encoding="utf-8")
    print("ADDED NEW TESTS")
else:
    print("ALREADY EXISTS")
