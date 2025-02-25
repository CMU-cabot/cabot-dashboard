import argparse


def load_env(file):
    return {p[0].strip(): p[1].strip() for p in (ln.split("=", maxsplit=1) for ln in file) if len(p) == 2 and "#" not in p[0]}


def dump_env(dict_env, file):
    for k, v in sorted(dict_env.items(), key=lambda x: x[0]):
        v and file.write(f"{k}={v}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="merge_env", description="Merge .env file")
    parser.add_argument("original", type=argparse.FileType("r", encoding="UTF-8"), help="Specify original .env file")
    parser.add_argument("update", type=argparse.FileType("r", encoding="UTF-8"), help="Specify .env file to merge")
    parser.add_argument("output", type=argparse.FileType("w", encoding="UTF-8"), help="Specify output .env file")
    args = parser.parse_args()
    dump_env(load_env(args.original) | load_env(args.update), args.output)
