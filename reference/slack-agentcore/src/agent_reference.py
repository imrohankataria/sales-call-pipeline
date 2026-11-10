"""Answer to the agent debugging mock. Read after your attempt."""


def run_agent(model, registry, max_steps=3):
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("Invalid max_steps")
    history = []
    for step in range(max_steps):
        action = model(list(history))
        if "final" in action:
            if not isinstance(action["final"],str):
                raise ValueError("Final answer must be string")
            return {"status":"completed", "answer":action["final"], "history":history}
        result = registry.dispatch(action)
        history.append({"action":action, "observation":result})
    return {"status":"max_steps", "answer":None, "history":history}
