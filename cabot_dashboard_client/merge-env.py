import argparse
import typing


def merge(original: typing.TextIO, update: typing.TextIO, result: typing.TextIO):
    def parse_kv(line: str):
        kv = line.strip().split("=", maxsplit=1)
        if len(kv) == 2:
            kv = kv[0].strip(), kv[1].strip()
            return None if kv[0].startswith("#") else kv

    result_dict = {}
    for kv in filter(lambda x: x, map(parse_kv, original.readlines())):
        if kv[1] != "":
            result_dict[kv[0]] = kv[1]
    for kv in filter(lambda x: x, map(parse_kv, update.readlines())):
        if kv[1] != "":
            result_dict[kv[0]] = kv[1]
        else:
            del result_dict[kv[0]]
    for key in sorted(result_dict):
        result.write(f"{key}={result_dict[key]}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="merge_env", description="Merge .env file")
    parser.add_argument("original", type=argparse.FileType("r", encoding="UTF-8"), help="Specify original .env file")
    parser.add_argument("update", type=argparse.FileType("r", encoding="UTF-8"), help="Specify .env file to merge")
    parser.add_argument("output", type=argparse.FileType("w", encoding="UTF-8"), help="Specify output .env  file")
    args = parser.parse_args()
    merge(args.original, args.update, args.output)
