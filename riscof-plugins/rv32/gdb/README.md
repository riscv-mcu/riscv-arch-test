## gdb plugin

This plugin allows the DUT to be a physical device connected to openocd and
driven by gdb. This requires you to have a riscv toolchain with gdb 
(built with `--with-python` to enable python scripting) as well
as openocd and a good openocd configuration file for your target device.
See `<path-to-plugins>/riscof-plugins/gdb/env/openocd-sample.cfg`
for a skeleton that you can adapt with details for you target.

To use the gdb plugin, add a `[gdb]` section to your config.ini. The following
example uses the traditional spike plugin as the reference and then gdb as the
DUT plugin. The config details include an additional field: `ocdcfg`. This is
the full path to your target's openocd configuration file. In the example below,
we're including a configuration file for spike. When using the gdb plugin with
openocd-spike.cfg, the plugin launches spike with a remote bitbang port open and
then connects to it with openocd and gdb. So yes, we're comparing spike to
spike, which is not apples to apples. 

You will also need to provide the `[spike]` node in the config.ini with the relevant 
ispec path and pspec path since the spike_simple pluging requires those as well

Sample config.ini:
```
[gdb]
ispec=<path-to-plugins>/riscof-plugins/gdb/gdb_isa.yaml
pspec=<path-to-plugins>/riscof-plugins/gdb/gdb_platform.yaml
ocdcfg=<path-to-plugins>/riscof-plugins/gdb/env/openocd-spike.cfg

```

**Currently, the gdb plugin is seeing a failure with EBREAK, because the plugin uses breakpoints through gdb.**


Currently, `gdb_isa.yaml` and `gdb_platform.yaml` specify a simple RV32IMC
target, but you can adjust these for your platform. Moving to RV64 will also
require some light tweaks to `riscof_gdb.py` and `env/run-test.py`. A simple
search for "32" will highlight the changes you need to make.

Lastly, it's somewhat robust, but you may have some issues when setting up your
target device. You may need to `kill -9` a few gdb, openocd, and/or spike
processes.
