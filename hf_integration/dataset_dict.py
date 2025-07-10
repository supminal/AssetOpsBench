# dataset.py
from datasets import GeneratorBasedBuilder, DatasetInfo, SplitGenerator
import json 

class AssetOpsBench(GeneratorBasedBuilder):
    def _info(self):
        return DatasetInfo(
            description="AssetOpsBench dataset with Scenarios and FailureSensorIQ tasks",
            features={},
            supervised_keys=None,
        )

    def _split_generators(self, dl_manager):
        data_dir = dl_manager.download_and_extract("data")
        return [
            SplitGenerator(name="scenarios", gen_kwargs={"filepath": f"{data_dir}/Scenarios.jsonl"}),
            SplitGenerator(name="failure_sensor_iq", gen_kwargs={"filepath": f"{data_dir}/FailureSensorIQ.jsonl"}),
        ]

    def _generate_examples(self, filepath):
        with open(filepath, encoding="utf-8") as f:
            for idx, line in enumerate(f):
                yield idx, json.loads(line)
