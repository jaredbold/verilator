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
import shutil
import subprocess
import tempfile

test.scenarios('dist')

perl = shutil.which('perl')
if not perl:
    test.skip('Perl is not installed')


def make_binary(directory, name):
    binary = directory / name
    binary.write_text(f'#!{perl}\nprint "SELECTED=$0\\n";\nprint "$_\\n" for @ARGV;\n'
                      'exit($ENV{VLCOV_TEST_STATUS} || 0);\n', encoding='utf8')
    binary.chmod(0o755)
    return binary


with tempfile.TemporaryDirectory(dir=test.obj_dir) as tmp:
    root = pathlib.Path(tmp).resolve()
    wrapper_dir = root / 'wrapper'
    install_dir = root / 'install'
    path_dir = root / 'path'
    work_dir = root / 'work'
    for directory in (wrapper_dir, install_dir / 'bin', path_dir, work_dir):
        directory.mkdir(parents=True)
    wrapper = wrapper_dir / 'verilator_coverage'
    shutil.copy2(os.environ['VERILATOR_ROOT'] + '/bin/verilator_coverage', wrapper)

    env = os.environ.copy()
    for key in ('VERILATOR_ROOT', 'VERILATOR_COVERAGE_BIN', 'POSIXLY_CORRECT',
                'VLCOV_TEST_STATUS'):
        env.pop(key, None)
    env['PATH'] = str(path_dir)

    def check(args, expected, overrides=None, status=0):
        test.oprint(f'Wrapper arguments: {args}, expected executable: {expected}')
        result = subprocess.run([perl, str(wrapper), *args],
                                cwd=work_dir,
                                env={**env, **(overrides or {})},
                                capture_output=True,
                                text=True,
                                check=False)
        if expected is None:
            if result.returncode == 0 or 'SELECTED=' in result.stdout:
                test.error('Missing executable unexpectedly ran: ' + result.stdout)
            if '%Error: Command Failed' not in result.stderr:
                test.error('Missing executable diagnostic not found: ' + result.stderr)
        else:
            if result.returncode != status:
                test.error(f'Expected exit {status}, got {result.returncode}: {result.stderr}')
            # --debug also prints the command; compare the executable's own output.
            selected = result.stdout.find('SELECTED=')
            if selected < 0 or result.stdout[selected:].splitlines() != [
                    'SELECTED=' + str(expected), *args
            ]:
                test.error('Wrong executable or forwarded arguments: ' + result.stdout)

    release_name = 'verilator_coverage_bin'
    debug_name = 'verilator_coverage_bin_dbg'
    release = make_binary(wrapper_dir, release_name)
    debug = make_binary(wrapper_dir, debug_name)

    check(['--version'], release)
    check(['--debug', '--version'], debug)
    for level in ('0', '5'):
        check(['--debugi', level, '--version'], debug)
        check(['input file.dat', '--debugi', level], debug, {'POSIXLY_CORRECT': '1'})
    check(['--version'], release, {'VLCOV_TEST_STATUS': '7'}, status=7)

    custom = make_binary(wrapper_dir, 'custom_coverage')
    override = {'VERILATOR_COVERAGE_BIN': custom.name}
    check(['--version'], custom, override)
    check(['--debugi', '5', '--version'], custom, override)
    custom.unlink()
    check(['--version'], None, override)

    release.unlink()
    check(['--version'], debug)
    debug.unlink()
    release = make_binary(wrapper_dir, release_name)
    check(['--debug', '--version'], None)
    check(['--debugi', '0', '--version'], None)
    release.unlink()
    check(['--version'], None)

    # An explicit root must take precedence over both the wrapper directory and PATH.
    make_binary(wrapper_dir, release_name)
    path_release = make_binary(path_dir, release_name)
    root_release = make_binary(install_dir, release_name)
    bin_release = make_binary(install_dir / 'bin', release_name)
    root_env = {'VERILATOR_ROOT': str(install_dir)}
    check(['--version'], bin_release, root_env)
    bin_release.unlink()
    check(['--version'], root_release, root_env)
    root_release.unlink()
    root_debug = make_binary(install_dir / 'bin', debug_name)
    check(['--version'], root_debug, root_env)
    check(['--debugi', '5', '--version'], root_debug, root_env)
    root_debug.unlink()
    check(['--version'], None, root_env)

    # With no root, look beside the wrapper first, then search PATH.
    check(['--version'], wrapper_dir / release_name)
    (wrapper_dir / release_name).unlink()
    check(['--version'], path_release)
    path_debug = make_binary(path_dir, debug_name)
    check(['--debugi', '5', '--version'], path_debug)
    path_release.unlink()
    check(['--version'], path_debug)
    path_debug.unlink()

    # Empty PATH entries search the working directory, including a trailing entry.
    local_release = make_binary(work_dir, release_name)
    make_binary(wrapper_dir, debug_name)
    for search_path in ('', str(path_dir) + os.pathsep):
        # PATH execution may preserve a relative argv[0].
        check(['--version'], pathlib.Path(release_name), {'PATH': search_path})
    local_release.unlink()

test.passes()
