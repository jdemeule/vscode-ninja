#!/usr/bin/env python3

import argparse
import glob
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback
import io


def extract_targets(build_path):
    targets = []
    p = subprocess.run(["ninja", "-C", build_path, "-t", "targets", "rule", "phony"],
                       stdout=subprocess.PIPE)
    if p.returncode == 0:
        output = io.StringIO(p.stdout.decode("utf-8"))
        for line in output:
            if not re.search("(cmake|edit_cache|rebuild_cache|install)", line, re.IGNORECASE):
                targets.append(line.rstrip('\n'))
    else:
        print("return code is %s" % p.returncode)
        print(p.stderr)
    return targets


def gen_build_task(target, build_path):
    return {
        "label": "build " + target,
        "group": "build",
        "type": "shell",
        "command": "ninja",
        "args": ["-C", build_path, target],
        "problemMatcher": {
            "owner": "cpp",
            "fileLocation": [
                "absolute"
            ],
            "pattern": {
                "regexp": "^(.*):(\\d+):(\\d+):\\s+(warning|error):\\s+(.*)$",
                "file": 1,
                "line": 2,
                "column": 3,
                "severity": 4,
                "message": 5
            }
        }
    }


def gen_run_task(build_path, target):
    args = []
    if target.endswith("test") or target.endswith("tests") or target.endswith("Test") or target.endswith("Tests"):
        args.append("--gtest_color=yes")
    return {
        "name": target,
        "type": "lldb",
        "program": "${{workspaceRoot}}/{}/bin/{}".format(build_path, target),
        "args": args,
        "env": {
            "DYLD_LIBRARY_PATH": "${{workspaceRoot}}/{}/lib".format(build_path)
        },
        "cwd": "${{workspaceRoot}}",
        "request": "launch",
    }


def guess_executables(targets):
    executables = []
    for t in targets:
        if not (t == "test" or t == "all" or t == "clean" or t.endswith(".dylib") or t.endswith(".dll") or t.endswith(".dll")):
            executables.append(t)
    return executables


def main():
    # Call ninja -C build-dir -t targets rule phony
    # Filter out cmake related stuff
    # Generate (or enrich?) in .vscode folder
    #   - tasks.json
    #   - launch.json
    parser = argparse.ArgumentParser(
        description='generate VSCode tasks.json and launch.json over Ninja')
    parser.add_argument('-p', dest='build_path',
                        help='Locate build folder')
    parser.add_argument('-o', dest='output_path',
                        help='Locate output vscode folder')
    args = parser.parse_args()
    build_path = "."
    if args.build_path is not None:
        build_path = args.build_path

    vscode_path = "."
    if args.output_path is not None:
        vscode_path = args.output_path

    targets = extract_targets(build_path)

    tasks = {
        "version": "2.0.0",
        "tasks": [gen_build_task(target, build_path) for target in targets]
    }
    # print(json.dumps(tasks, indent=4))
    with open(os.path.join(vscode_path, "tasks.json"), "w") as task_json:
        json.dump(tasks, task_json, indent=4)

    executable_targets = guess_executables(targets)
    launch = {
        "version": "0.2.0",
        "configurations": [gen_run_task(build_path, t) for t in executable_targets]
    }
    # print(json.dumps(launch, indent=4))
    with open(os.path.join(vscode_path, "launch.json"), "w") as launch_json:
        json.dump(launch, launch_json, indent=4)

    pass


if __name__ == "__main__":
    main()
