DeepQA_AGENT_FEW_SHOTS = """
"""

DeepQA_AGENT_ADDITIONAL_FEW_SHOTS = """
"""

def get_deepqa_agent_examples(include_additional=False):
    examples = DeepQA_AGENT_FEW_SHOTS.strip()
    if include_additional:
        examples += "\n\n" + DeepQA_AGENT_ADDITIONAL_FEW_SHOTS.strip()
    return examples