import argparse
import typing


def load_key_values(file: typing.TextIO):
    def parse_kv(line: str):
        kv = line.strip().split("=", maxsplit=1)
        if len(kv) == 2 and "#" not in kv[0]:
            return kv[0].strip(), kv[1].strip()

    return filter(lambda kv: kv, map(parse_kv, file.readlines()))


def merge(original: typing.TextIO, update: typing.TextIO, result: typing.TextIO):
    result_dict = {}
    for key, value in load_key_values(original):
        if value:
            result_dict[key] = value
    for key, value in load_key_values(update):
        if value:
            result_dict[key] = value
        else:
            del result_dict[key]
    for key in sorted(result_dict):
        result.write(f"{key}={result_dict[key]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="merge_env", description="Merge .env file")
    parser.add_argument("original", type=argparse.FileType("r", encoding="UTF-8"), help="Specify original .env file")
    parser.add_argument("update", type=argparse.FileType("r", encoding="UTF-8"), help="Specify .env file to merge")
    parser.add_argument("output", type=argparse.FileType("w", encoding="UTF-8"), help="Specify output .env file")
    args = parser.parse_args()
    merge(args.original, args.update, args.output)
