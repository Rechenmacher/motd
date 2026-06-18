"""python -m motd  — print a random message to stdout"""
import argparse
from . import format_message, random_message


def main():
    parser = argparse.ArgumentParser(description="Print a random Message of the Day")
    parser.add_argument("--tag", help="Filter by tag (funny, tech, wisdom, ...)")
    args = parser.parse_args()
    print(format_message(random_message(tag=args.tag)))


if __name__ == "__main__":
    main()
