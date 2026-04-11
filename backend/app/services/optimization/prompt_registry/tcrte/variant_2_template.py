def build_tcrte_variant_2_system_prompt(*, role_section: str, task_section: str, context_section: str, tone_section: str, execution_section: str, constraints_text: str) -> str:
    return f"""### ROLE
{role_section}

### TASK
{task_section}

### CONTEXT
{context_section}

### TONE
{tone_section}

### EXECUTION
{execution_section}

### CONSTRAINTS
{constraints_text}"""