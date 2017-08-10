# Some disk metrics plugins for the datadog agent

I kinda want to know about the health of my home system, so I wrote
these checks. They kinda measure the right thing for the disks that
I'm running, but your requirements may differ, so please use with
caution and definitely evaluate what `smartmontools` and `nvme` 
metrics make sense for your system.

In particular, this tool alerts based on the "raw" value that 
`smartctl` emits. These can sometimes be misleading, so definitely 
check with your disk vendor!

## Security considerations

Also, they use `sudo`, so you will need a sudoers file. 
A `sudoers.d` file is provided in examples/ - please study it and 
adjust as you need. (In particular, you may not need the `selftest` 
command for `smartctl`.
