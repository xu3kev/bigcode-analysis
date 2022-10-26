import time
from datasets import load_dataset
from tqdm import tqdm
import argparse


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Config and test files detection"
    )
    parser.add_argument(
        "--dataset_name",
        default="bigcode/python_permissive",
        type=str,
        help="HF repo name/path of the dataset.",
    )
    parser.add_argument(
        "--num_workers",
        default=96,
        type=int,
        help="Number f workers for multiprocessing",
    )
    parser.add_argument(
        "--text_column",
        default="content",
        type=str,
        help="Text column name",
    )
    parser.add_argument(
        "--push_to_hub",
        action="store_true",
        help="Push the dataset to the Hub",
    )
    return parser.parse_args()


def is_config_or_test(example, scan_width=5, coeff=0.05):
    """Check if file is a configuration file or a unit test by :
    1- looking for keywords in the first few lines of the file.
    2- counting number of occurence of the words 'config' and 'test' with respect to number of lines.
    """

    keywords = ["unit tests", "test file", "configuration file"]
    lines = example["content"].splitlines()
    count_config = 0
    count_test = 0
    # first test
    for _, line in zip(range(scan_width), lines):
        for keyword in keywords:
            if keyword in line.lower():
                return {"config_or_test": True}
    # second test
    nlines = example["content"].count("\n")
    threshold = int(coeff * nlines)
    for line in lines:
        count_config += line.lower().count("config")
        count_test += line.lower().count("test")
        if count_config > threshold or count_test > threshold:
            return {"config_or_test": True}
    return {"config_or_test": False}


def preprocess(example):
    results = dict()
    results.update(is_config_or_test(example))
    return results


def filter(example, args):
    """Filter dataset with heuristics. Config, test and has_no_keywords files are removed with a given probability."""
    if example["config_or_test"]:
        return False
    else:
        return True


args = parseArgs()

# Load dataset
t_start = time.time()
print(f"Loading dataset {args.dataset_name}")
dataset = load_dataset("bigcode/the-stack", data_files = ["data/python/*"], split="train", use_auth_token=True, chunksize=40<<20)
print(f"Time to load dataset: {time.time()-t_start:.2f}")

# Run preprocessing
t_start = time.time()
ds = dataset.map(preprocess, num_proc=args.num_workers)
print(f"Time to preprocess dataset: {time.time()-t_start:.2f}")
print(ds)

t_start = time.time()
old_size = len(ds)
ds = ds.filter(filter, fn_kwargs={"args": args})
print(f"Time to filter dataset: {time.time()-t_start:.2f}")
print(f"\nSize of original dataset: {old_size}")
print(f"Size of filtered dataset: {len(ds)}")
print(f"\nPercentage of removed files: {(old_size - len(ds))*100/old_size}")
print(f"Percentage of left files: {(len(ds))*100/old_size}%")

print("\nCounting size in Gb of the new datase")
new_size, old_size = 0, 0
for i in tqdm(range(len(ds))):
    new_size += len(ds[i]["content"])

for i in tqdm(range(len(dataset))):
    old_size += len(dataset[i]["content"])

print(f"current size in Gb is {new_size/10**9}")
print(f"old size in Gb is {old_size/10**9}")
print(f"volume removed: {(new_size-old_size)*100/new_size}%")

if args.push_to_hub:
    ds.push_to_hub("no_conf_test_ds")
