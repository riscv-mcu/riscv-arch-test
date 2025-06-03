import os
import re
import shutil
import subprocess
import shlex
import logging
import random
import string
from string import Template
import sys

import riscof.utils as utils
from riscof.pluginTemplate import pluginTemplate
import riscof.constants as constants

logger = logging.getLogger()

map = {
    'rv32i': 'rv32i',
    'rv32im': 'rv32im',
    'rv32ic': 'rv32ic',
    'rv32ia': 'rv32ia'
}


class gdb(pluginTemplate):
    def __init__(self,*args,**kwargs):
        sclass = super().__init__(*args,**kwargs)

        config = kwargs.get('config')
        if config is None:
            print("Please enter input file paths in configuration.")
            raise SystemExit
        else:
            self.isa_spec = os.path.abspath(config['ispec'])
            self.platform_spec = os.path.abspath(config['pspec'])
            self.openocd_cfg = os.path.abspath(config['ocdcfg'])

        if self.openocd_cfg is None:
            print("gdb configuration requires an openocd cfg file.")
            raise SystemExit

        compile_flags = ' -static -mcmodel=medany -fvisibility=hidden \
        -nostdlib -nostartfiles '

        self.pref = "riscv32-unknown-elf-"
        self.gcc = "riscv32-unknown-elf-" + 'gcc'
        self.ld = "riscv32-unknown-elf-" + 'ld'
        self.root_dir = constants.root
        self.env_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                    "env")
        self.linker = os.path.join(self.env_dir, "link.ld")
        self.user_abi = "ilp32"
        self.user_target = "SPIKE"
        self.user_sign = "sign"
        self.objdump = "riscv32-unknown-elf-" + 'objdump -D '
        self.compile_cmd = self.gcc+ ' -march={0} -mabi={1} '+compile_flags +\
                ' -T'+self.linker
        self.objdump = "riscv32-unknown-elf-" + 'objdump -D'
        return sclass

    def initialise(self, suite, work_dir, env):
        self.suite = suite
        self.work_dir = work_dir
        self.compile_cmd = self.compile_cmd + " -I" + env + " -I" + self.env_dir

    def build(self,isa_spec,platform_spec):
        ispec = utils.load_yaml(isa_spec)['hart0']
        self.isa = ispec["ISA"]

    def runTests(self, testlist):
        foo = os.path.join(self.work_dir, "Makefile." + self.name[:-1])
        tlist = 'make -j 1 -f ' + foo + " " # + " -T ./" + self.name[:-1] + ".log "
        #print(tlist)
        with open(foo, "w") as makefile:
            for file in testlist:
                testentry = testlist[file]
                #print(testentry)
                target = str(file.split("/")[-1][:-2])
                tlist += target + " "
                makefile.write("\n\n.PHONY : " + target + "\n" + target + " :")
                test = os.path.join(self.root_dir, str(file))
                test_dir = testentry['work_dir']
                elf = os.path.join(test_dir,
                                   str(file.split("/")[-1][:-2]) + '.elf')
                cmd = self.compile_cmd.format(
                    testentry['isa'].lower(),
                    self.user_abi) + ' ' + test + ' -o ' + elf
                execute = cmd + ' -D' + " -D".join(testentry['macros'])
                makefile.write("\n\techo \"Running " + target + "\"\n\t" +
                               execute)
                cmd = self.objdump.format(test, self.user_abi) + ' ' + elf
                makefile.write("\n\t" + cmd + ' > {0}/{1}.disass'.format(
                    testentry['work_dir'], str(file.split("/")[-1][:-2])))

                elf = os.path.join(test_dir,
                                   str(file.split("/")[-1][:-2]) + '.elf')
                d = dict(elf=elf, testDir=test_dir, isa=self.isa)

                command = Template(
                    "cd " + testentry['work_dir'] +
                    ';ln -sf ' + self.env_dir + '/run-test.py ./' +
                    ';riscv32-unknown-elf-gdb' +
                    ' -ex "py elf = \'${elf}\'"' +
                    ' -ex "py cfg = \'' + self.openocd_cfg + '\'"' +
                    ' -ex "py sigout = \'sign\'"' +
                    ' -x "run-test.py" > log.txt;'
                ).safe_substitute(d)
                makefile.write("\n\t" + command)

                sign_file = os.path.join(test_dir,
                                         self.name[:-1] + ".signature")
                cp = "cat " + os.path.join(test_dir, "sign") + " > " + sign_file
                makefile.write("\n\t" + cp)
        utils.shellCommand(tlist).run(cwd=self.work_dir)
