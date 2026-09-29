#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2024 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('dist')

for basename in [
        "t_vlcov_data_a.dat", "t_vlcov_data_b.dat", "t_vlcov_data_c.dat", "t_vlcov_data_d.dat"
]:
    test.run(cmd=[
        os.environ["VERILATOR_ROOT"] + "/bin/verilator_coverage", "t/" + basename, "--debug",
        "--debugi 9"
    ],
             tee=test.verbose,
             verilator_run=True)

# Exercise --debugi alone and check that the requested logging level takes effect.
for level in (0, 2, 9):
    logfile = test.obj_dir + '/debugi_' + str(level) + '.log'
    test.run(cmd=[os.environ['VERILATOR_ROOT'] + '/bin/verilator_coverage',
                  't/t_vlcov_data_a.dat', '--debugi', str(level)],
             logfile=logfile,
             tee=test.verbose,
             verilator_run=True)
    if level:
        test.file_grep(logfile, r'readCoverage t/t_vlcov_data_a.dat')
    else:
        test.file_grep_not(logfile, r'readCoverage')

test.passes()
