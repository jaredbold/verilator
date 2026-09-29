#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2024 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
import shlex

test.scenarios('dist')

if not os.path.exists(test.root + "/.git"):
    test.skip("Not in a git repository")

cwd = os.getcwd()
destdir = cwd + "/" + test.obj_dir

# Start clean
test.run(cmd=["rm -rf " + destdir + " && mkdir -p " + destdir], check_finished=False)

# Install into temp area
print("Install...")
test.run(
    cmd=["cd " + test.root + " && " + os.environ["MAKE"] + " DESTDIR=" + destdir + " install-all"],
    check_finished=False)

# The wrapper's debug fallback must not hide a missing optimized executable.
for name in ('verilator_coverage_bin', 'verilator_coverage_bin_dbg'):
    installed = [os.path.join(directory, filename)
                 for directory, _, filenames in os.walk(destdir)
                 for filename in filenames if filename in (name, name + '.exe')]
    if not installed:
        test.error('Missing installed coverage executable: ' + name)
    for filename in installed:
        if not os.access(filename, os.X_OK):
            test.error('Installed coverage executable is not executable: ' + filename)
        test.run(cmd=[shlex.quote(filename), '--version'], tee=test.verbose,
                 verilator_run=True)

# Check we can run a test
# Unfortunately the prefix was hardcoded in the exec at a different place,
# so we can't do much here.
#print("Check install...")

# Uninstall
print("Uninstall...\n")
test.run(
    cmd=["cd " + test.root + " && " + os.environ["MAKE"] + " DESTDIR=" + destdir + " uninstall"],
    check_finished=False)

# Check empty
files = []
finds = test.run_capture("find " + destdir + " -type f -print")
for filename in finds.split():
    if re.search(r'\.status', filename):  # Made by driver.py, not Verilator
        continue
    print("\tLEFT:  " + filename)
    filename = re.sub(r'^' + re.escape(cwd), '.', filename)
    files.append(filename)

if len(files) > 0:
    test.error("Uninstall missed files: " + ' '.join(files))

test.passes()
