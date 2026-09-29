#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
import pathlib
import shlex
import shutil

test.priority(100)
test.scenarios('dist')

source_dir = pathlib.Path(test.root).resolve()
obj_dir = pathlib.Path(test.obj_dir).resolve()
if not (source_dir / 'configure').exists() or not (source_dir / 'src/Makefile.in').exists():
    test.skip('Requires a source tree with configure generated')
if not shutil.which('cmake'):
    test.skip('CMake is not installed')

# Generated Autoconf headers in the checkout can override CMake's headers.
# Copy the build inputs so neither build system affects the enclosing build.
build_source = obj_dir / 'source'
if build_source.exists():
    shutil.rmtree(build_source)
build_source.mkdir()
for name in ('CMakeLists.txt', 'Makefile.in', 'configure', 'install-sh',
             'verilator-config.cmake.in', 'verilator-config-version.cmake.in', 'verilator.pc.in'):
    shutil.copy2(source_dir / name, build_source / name)
for name in ('bin', 'include', 'src'):
    shutil.copytree(source_dir / name, build_source / name,
                    ignore=shutil.ignore_patterns('obj_*', '__pycache__', 'Makefile',
                                                 'Makefile_obj', 'config_package.h',
                                                 'config_rev.h', 'verilated_config.h',
                                                 'verilated.mk', 'verilator_bin*',
                                                 'verilator_coverage_bin*', '*.d', '*.log'))
source_dir = build_source


def run_build(cmd, directory, logname):
    test.run(cmd=['cd', shlex.quote(str(directory)), '&&', shlex.join(cmd)],
             logfile=str(obj_dir / logname),
             tee=test.verbose)


def check_binary(binary, directory):
    if not binary.is_file() or not os.access(binary, os.X_OK):
        test.error('Missing coverage executable: ' + str(binary))
    output = directory / (binary.name + '.info')
    logfile = str(directory / (binary.name + '.log'))
    test.run(cmd=[shlex.quote(str(binary)), '--write-info',
                  shlex.quote(str(output)), 't/t_vlcov_data_a.dat', 't/t_vlcov_data_b.dat',
                  't/t_vlcov_data_c.dat', 't/t_vlcov_data_d.dat'],
             logfile=logfile,
             tee=test.verbose,
             verilator_run=True)
    test.files_identical(str(output), 't/t_vlcov_info.info.out')
    test.file_grep_not(logfile, r'readCoverage')


# Build the coverage targets only; rebuilding the compiler is unnecessary here.
for mode in ('release', 'combined'):
    build_dir = obj_dir / ('cmake_' + mode)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    options = ['-DCMAKE_BUILD_TYPE=CoverageRelease'] if mode == 'release' else [
        '-DDEBUG_AND_RELEASE_AND_COVERAGE=ON'
    ]
    run_build(['cmake', '-G', 'Unix Makefiles', '-S', str(source_dir), '-B', str(build_dir),
               *options], obj_dir, mode + '_configure.log')
    targets = ['verilatorCoverageRelease']
    if mode == 'combined':
        targets.append('verilatorCoverage')
    run_build(['cmake', '--build', str(build_dir), '--parallel', '2', '--target', *targets],
              obj_dir, mode + '_build.log')
    release_dir = build_dir / ('src' if mode == 'release' else 'build-CoverageRelease')
    check_binary(release_dir / 'verilator_coverage_bin', build_dir)
    if mode == 'combined':
        check_binary(build_dir / 'build-Coverage/verilator_coverage_bin_dbg', build_dir)

# Exercise GNU Make's real optimized build, then its debug-only copy fallback.
build_dir = obj_dir / 'make'
if build_dir.exists():
    shutil.rmtree(build_dir)
build_dir.mkdir()
run_build([str(source_dir / 'configure'), '--enable-ccwarn'], build_dir, 'make_configure.log')
make_cmd = shlex.split(os.environ['MAKE']) + ['-C', str(build_dir / 'src'), '-j2']
run_build(make_cmd + ['VERILATOR_NO_OPT_BUILD=0', '../bin/verilator_coverage_bin',
                      '../bin/verilator_coverage_bin_dbg'],
          build_dir, 'make_build.log')
release = build_dir / 'bin/verilator_coverage_bin'
debug = build_dir / 'bin/verilator_coverage_bin_dbg'
check_binary(release, build_dir)
check_binary(debug, build_dir)
release.unlink()
run_build(make_cmd + ['VERILATOR_NO_OPT_BUILD=1', '../bin/verilator_coverage_bin'],
          build_dir, 'make_no_opt_build.log')
if release.read_bytes() != debug.read_bytes():
    test.error('VERILATOR_NO_OPT_BUILD did not copy the debug coverage executable')
check_binary(release, build_dir)

test.passes()
