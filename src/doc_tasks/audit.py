"""Local, inspectable evidence for every accepted and rejected model decision."""
import copy


class AuditedDecisions:
    def __init__(self, client):
        self.client = client
        self.model = client.model
        self.trace = []

    @property
    def calls(self):
        return self.client.calls

    @property
    def elapsed(self):
        return self.client.elapsed

    def evaluate(self, state, questions):
        answers = self.client.evaluate(state, questions)
        self.trace.append({"state": copy.deepcopy(state),
                           "questions": [q.model_dump() for q in questions],
                           "answers": {key: answer.model_dump() for key, answer in answers.items()}})
        return answers

    def close(self):
        self.client.close()
