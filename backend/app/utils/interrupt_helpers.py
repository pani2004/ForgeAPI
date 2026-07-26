def extract_interrupt(result: dict | list) -> dict | None:
    """
    LangGraph returns interrupts under __interrupt__.
    """
    if isinstance(result, dict) and "__interrupt__" in result:
        interrupts = result["__interrupt__"]
        if interrupts:
            first = interrupts[0]
            return getattr(first, "value", first)
    return None


async def get_pending_interrupt(workflow, config) -> dict | None:
    snapshot = await workflow.aget_state(config)
    if not snapshot:
        return None

    for task in snapshot.tasks or []:
        if getattr(task, "interrupts", None):
            interrupt_obj = task.interrupts[0]
            return getattr(interrupt_obj, "value", interrupt_obj)

    return None