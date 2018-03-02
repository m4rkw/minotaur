# Minotaur, gpustatd and Excavataur by m4rkw

## WARNING

MINOTAUR SUPPORTS OVERCLOCKING. OVERCLOCKING CAN DAMAGE YOUR HARDWARE IF
ENABLED. YOU ASSUME ANY AND ALL RISK ASSOCIATED WITH OVERCLOCKING BY THE USE OF
THIS SOFTWARE. WE ARE NOT RESPONSIBLE FOR ANY DAMAGE THAT MAY ARISE FROM THE USE
OF THIS SOFTWARE. SEE THE LICENSE TERMS FOR MORE INFORMATION.


## Projects

These three projects are designed to work together:

- gpustatd - https://github.com/m4rkw/gpustatd
- Minotaur - this one you're looking at :)
- Excavataur - https://github.com/m4rkw/excavataur


## Updates

- 06/02/2018 - Minotaur v0.9 now supports ethereum pool mining via
ethermine.org! You'll need the latest version of Excavataur for this to work.

- 11/02/2018 - Minotaur v0.9.8.6 now supports ZEC pool mining via flypool.

- 13/02/2018 - Minotaur v0.9.9 now supports XMR pool mining via Monero Ocean.

- 15/02/2018 - As of Minotaur v0.9.9.8 fanotaur is now gpustatd.

- 18/02/2018 - New features in Minotaur 1.0:

- Added support for zclmine.pro and miningpoolhub

- 20/02/2018 - Minotaur now has generic support for any pool you want to use!

- 02/03/2018 - Minotaur is now completely free and open source

## Support channel

Join us in #minotaur on the freenode network - https://freenode.net

````
/server irc.freenode.net
/join #minotaur
````

## Overview

Minotaur is a miner management system designed to maximise profit. It has been
primarily designed to work with Nicehash and the Excavator miner but also has
support for two variants of ccminer, xmrig-nvidia, ethminer and ewbf. Support for
these miners is enabled via the shim project Excavataur. It is our intention
to add support for as many miners as possible including CPU miners in the near
future.  

Pools supported:

- nicehash
- miningpoolhub
- any single-coin pool you want to use

## Quickstart

If you don't want to read all this documentation and just want to get mining as
fast as possible you can use quickstart mode:

````
$ ./minotaur --quickstart
````

Quickstart mode will run the calibration process for the 5 most profitable GPU
algorithms on Nicehash (currently equihash, nist5, neoscrypt, keccak, lyra2rev2)
using default config on all of your device classes (by default a device class is
the same as a model name, eg "1070ti". This calibration only needs to happen
once - once they have been calibrated across all of your device classes next
time you can just run:

````
$ ./minotaur --mine
````

Note that you may want to edit some parameters in the default config before
running quickstart mode. You will need at least one miner configured for this
to work. Excavator is configured by default so as long as you have excavator
running on the default port (3456) this should work.

You may get more benefit out of running full power calibration as described
below but if you're keen to get up and running quickly you can do this one
device at a time while the others mine.

## Power calibration

Minotaur runs a series of tests with a given algorithm on a given device in
order to determine the optimum hashrate at the optimum power level. This process
is highly configuration but I recommend using the defaults.  

These tests can take some time to complete, especially if you run them on all of
the available algorithms, but the results are worth it. We often find that some
devices run algorithms faster at lower power limits, and frequently find that a
lower power limit doesn't affect the hashrate - saving you money.

## Algorithm selection

Minotaur takes four sources of data:

- the current market rates for all of the algorithms on Nicehash
- your calibrated hashrate for each algorithm
- your optimal power limit for each algorithm observed during calibration
- your configured power costs

Using this data it can decide which is the most profitable algorithm to mine
from moment to moment base on market price, hashrate and power consumption vs
power cost. Currently it checks the Nicehash API every 15 seconds.

## Device/algorithm profiles

Minotaur lets you create profiles that target either a device, an algorithm or a
device/algorithm combination. In these profiles you can set:

- gpu clock offset
- memory clock offset

Note: as of version 1.0 we no longer support configuring a power limit in the
device profiles. Power limits are solely derived from the calibration files in
~/.minotaur/ however you can edit these manually as you wish.

We do not endorse or recommend overclocking - do so at your own risk!

## Monitoring

Minotaur has a top-style ncurses interface for monitoring your devices.

Invoke it with:

````
./minotaur --gs
````

You can also have it write the display out as html on a 1-second interval:

````
./minotaur --html <filename>
````

![minotaur](https://a.rkw.io/minotaur.png?t=1)

# Compatibility

- Hardware: Nvidia only for now. CPU miner support is planned soon.
- Miners:

- Excavator - https://github.com/nicehash/excavator
- xmrig-nvidia - https://github.com/xmrig/xmrig-nvidia
- ccminer (tpruvot) - https://github.com/tpruvot/ccminer.git
- ccminer2 (alexis78) - https://github.com/alexis78/ccminer.git
- ethminer - https://github.com/ethereum-mining/ethminer
- ewbf - https://github.com/nanopool/ewbf-miner

Note: "ccminer2" is just the name of the alexis78 fork within Minotaur and
Excavataur.

We can easily add other miners so you are welcome to open github issues with
requests.

See: https://github.com/m4rkw/minotaur/blob/master/BENCHMARKS.txt

for an idea of how these miners perform with various algorithms. More data
will be added to this file over time.


# Usage

1. Set up a Xorg display such that you can use nvidia-settings. Make sure the
user you will run Minotaur as is able to use it and change card settings.

2. Install and configure gpustatd

https://github.com/m4rkw/gpustatd

This will control your GPU fans independently of Minotaur in order to keep
temperatures under control. Minotaur does not ever touch fan speeds, but by
default it will throttle the power limit in order to try keep the GPU under
80C.

3. If you want to use any miners other than Excavator, you'll need to install
and configure Excavataur. This is a related project which provides a
trimmed-down clone of the Excavator JSON API as a wrapper around cli miners.
This shim interface makes it very easy for us to add additional miner tools to
the project.

https://github.com/m4rkw/excavataur

4. Copy minotaur.conf and edit it to your liking (full config reference below).

Minotaur will look for its config file at the following locations:

- /etc/minotaur.conf
- ./minotaur.conf
- ~/.minotaur/minotaur.conf

5. Before you can start mining with Minotaur you need to run the calibration
process for each algorithm/device combination. By default you can target devices
based on their model designation (eg "1080Ti") but we also have supported for
defining device classes within the same model range. This is useful if you have
cards that are the same model number but from different manufacturers.

You only need to calibrate each device class once for each algorithm, so if you
have 4 1070s you can distribute the calibration across them to get it done
quicker.


## Calibration

To see the calibration options:

````
$ ./minotaur --calibrate
````

Calibrate all excavator algorithms in eu region on device 0:

````
$ ./minotaur --calibrate 0 nicehash excavator all eu
````

Calibrate all excavator algorithms in eu region on all device classes:

````
$ ./minotaur --calibrate all nicehash excavator all eu
````

Calibrate nist5, neoscrypt and equihash:

````
$ ./minotaur --calibrate 0 nicehash excavator nist5,neoscrypt,equihash eu
````

Calibrate all excavator algorithms in eu region except for nist5:

````
$ ./minotaur --calibrate 0 nicehash excavator all,\!nist5 eu
````

Device classes are shortened, so for example "Geforce GTX 1070 Ti" becomes
"1070Ti".

Minotaur's calibration process allows you to automatically determine your
nominal hashrate at the lowest power limit that doesn't compromise the hashrate.
See the config params under the "calibration" section. The most important value
to look at is "acceptable_loss_percent" which defaults to 1%. This means we will
accept a loss of 1% hashrate if we can run an algorithm at a lower power limit.

Calibration files are stored in simple plaintext YAML in ~/.minotaur/.

The full calibration process is:

2. Initial run to establish a baseline hashrate.

config:

````
calibration:
  hashrate_stabilisation_timeout_mins: 10
  hashrate_stabilisation_tolerance: 0.5
  algorithm_start_timeout: 180
````

It will run until the hashrate is stable - 5 consecutive readings within 1%
of eachother. You can adjust the tolerance using the parameters above. You can
use fractional values for the tolerance value, eg 0.5.

````
calibration:
  initial_sample_time_mins: 10
````

2. If power tuning is enabled Minotaur will then attempt to determine the lowest
power limit that we can run the algorithm with without losing more than our
acceptable hashrate %. The first step is to decrease the power limit to the
level observed at the max power draw in step 2.

3. If the rate doesn't fall by more than the configured loss % then it will keep
going in 10W decrements until the rate falls by more than 1% (or whatever you've
set it to). When this happens it will try dialling back 5W to see if that
mitigates the loss.

4. This process is repeated in 5-min runs until the optimum power limit is
found. In testing we frequently found that hashrates would sometimes go *up*
rather than down when the power limit was lowered.

Relevant config params:

````
calibration:
  power_tuning:
    enable: true
    decrement_watts: 10
    acceptable_loss_percent: 1
````

Note that acceptable_loss_percent should be at least 2x the setting for
hashrate_stabilisation_tolerance otherwise you're just measuring noise.

As of 0.9.8 Minotaur can now update the calibration data over time with data
from normal mining runs. This is useful if the conditions of your system change
over time. There is a fixed period of update_calibration_data_after_mins
minutes that an algorithm must run for before it will be considered for an
update and the hashrate must be within the configure percentage limit (see
below). The rate must also be considered stable so the variance must be within
the percentage defined in the hashrate_stabilisation_tolerance setting for a
number of readings equal to your
hashrate_stabilisation_consecutive_readings_required setting.

````
  update_calibration_data_over_time: true
  calibration_update_threshold_min_pc: 3
  calibration_update_threshold_max_pc: 10
````

Calibration runs are logged to /var/log/minotaur/calibration_{device_id}.log.

If you're just interested in getting up and running as fast as possible you can
specify --quick when calibrating to skip the power calibration phase and
optionally you can also set the warm-up cycle to 0 in the config which will
disable it.


# Mining

Once you have some calibration data for at least one algorithm you can start
mining. Simply run minotaur and it will talk to the Nicehash API and mine the
most profitable algorithms based on the current market rates and your calibrated
hashrates.

Minotaur periodically reloads its calibration data and you can also trigger this
with a HUP which will also reload the config. This means if you start with one
algorithm and then start calibrating others, Minotaur will pick up the new
calibrated algorithms more or less as soon as they are available.

A HUP signal also reloads and re-applies the device profiles for active cards so
you can tweak overclock settings on the fly.

If you want to mine with some cards and calibrate with others you can explicitly
set cards as ignored in the config file:

````
ignore_devices: [0,1]
````

This will ignore GPUs 0 and 1 when running with --mine but you can still target
them with --calibrate. A another way is using the --force parameter to with
--calibrate. By default if a card is mining, --calibrate will refuse to run.
However if you specify --force it will stop the mining worker and mark the card
as being used for calibration until its finished. Minotaur will detect this and
ignore the card until its free for user again.

Although this mostly works, there is the potential for some race condition
issues so I would advise using the ignore_devices setting rather than this. The
benefit of using --force is that if Minotaur is running then the card will be
immediately returned to mining as soon as the calibration run is complete.
Although most of the time it works fine, you will occasionally run into race
condition issues and end up with two mining processes at the same time.

Erraneous workers can be cleaned up with:

````
./minotaur --cleanup <device_id>
````

# Mining pool hub

This pool is slightly different in that you need to configure the hub workers
yourself in your miningpoolhub account before they will authenticate. Create one
for each auto-switching algorithm you want to mine. We currently only support
cryptonight, equihash, daggerhashimoto (ethhash), lyra2rev2, neoscrypt and keccak.
Once you've configured the workers in your miningpoolhub account (make sure they
all have the password 'x') you can configure the worker names in minotaur.conf.
See the example config file for an example of how to do this.

If you want to be able to calibrate using this pool you will also need to create
duplicate hub workers with "CALIB" appended to the worker name.


# Device profiles

Minotaur allows you to configure device profiles that are assigned to a device
class, an algorithm or a combination of the two. Currently device profiles allow
you to specify a power limit, gpu clock offset and memory clock offset.

Minotaur will look for a specific profile (where device and algorithm both
match) before looking for more generic profiles where say the device matches but
the algorithm is "all".

In order to change the clocks you will also need to explicitly disable the
"leave_graphics_clocks_alone" setting.

It is recommended not to set the power limit in a device profile but rather use
the power limit obtained via calibration. The power limit set in a device
profile will override that found via calibration. Profile settings from the
default profile are inherited by other profiles.


# Device classes

If you have several cards of the same model number but from different
manufacturers you can define custom device classes to group them separately and
thus apply device profiles to groups of them.

Here's an example of this in minotaur.conf:

````
device_classes:
  "1080ti_asus":
    - 0
    - 1
  "1080ti_evga":
    - 2
    - 3
````

The numbers are the GPU ids returned by nvidia-smi.


## Overclocking notes

If you are going to overclock your card aggressively for mining you probably
want to consider using device profiles within Minotaur rather than setting the
clocks externally. The reason for this is that the clocks are an offset from the
current base clock which varies depending on whether the card is in P0 or P2 mode.
If you set an aggressive clock boost and start mining the card will enter P2
mode. As soon as the worker is stopped the card jumps back into P0 mode which
has higher base clocks and this can trigger a crash.

If you use device profiles within Minotaur, the default profile will always
be loaded before stopping a worker and a device profile will always be loaded
*after* the worker has started. This should ensure that you don't run into
crashes with high overclock settings and state transitions.

Note: if you set GPU or memory clock offsets in the default profile they will be
ignored and unless you have explicitly enabled the "leave_graphics_clocks_alone"
option, clock offsets will be set to 0 whenever the default profile is loaded.
This is a safety mechanism to avoid crashes during P0/P2 state transitions.

Of course you overclock entirely at your own risk and Minotaur cannot guarantee
that this scenario will not occur via some other means.


# Device pinning

You can now pin a device to a specific miner/algorithm/region combination for
testing. See --help for syntax.


# Self-upgrade

You can upgrade to the latest release with:

````
minotaur --upgrade
````


# GS display

Minotaur comes with a top-style monitoring interface which provides metrics on
all of your devices. You can start it with:

````
minotaur --gs
````

Relevant config params:

````
live_data:
  profitability_averages:
    - 900
    - 3600
    - 86400
  power_draw_averages:
    - 300
    - 600
    - 900
electricity_per_kwh: 0.1194
electricity_currency: GBP
system_draw_watts: 200
````

system_draw_watts is the wattage used by the rest of the system, eg other than GPUs.
Setting this allows for more accurate profit calculation.


# Stat collection

By default Minotaur will collect stats in CSV format in /var/log/minotaur/.
There is currently one simple report that you can execute:

````
$ ./minotaur.py --stats

stats for the last 24 hours:

 from: 2018-02-08 13:10:13
   to: 2018-02-08 21:44:42

total: 0.44 mBTC
  GBP: 2.65

 rate: 1.24 mBTC/day
  GBP: 7.42/day
  GBP: 222.58/month

income by algorithm:

       equihash: 0.1937 mBTC  1.16 GBP
        x11gost: 0.1027 mBTC  0.62 GBP
daggerhashimoto: 0.0650 mBTC  0.39 GBP
         keccak: 0.0280 mBTC  0.17 GBP
      neoscrypt: 0.0278 mBTC  0.17 GBP
      lyra2rev2: 0.0238 mBTC  0.14 GBP
          nist5: 0.0010 mBTC  0.01 GBP
````

You can also pass a number after --stats to see a report for a different number of
preceding hours, eg to see the last hour:

````
./minotaur.py --stats 1
````


# Full configuration reference

````
nicehash.primary_region
````

Primary Nicehash region to use. Currently only eu and usa are supported as the
other regions are just proxies and the payrate data only differentiates between
eu/usa.

````
nicehash.failover_regions
````

A list of Nicehash regions to fail over to if the primary region fails.
Currently only eu and usa are supported.

````
nicehash.user
````

Your nicehash username.

````
nicehash.worker_name
````

Your nicehash worker name

````
nicehash.append_device_id_to_worker_name
````

If enabled this will append the device id of your Nvidia card to the worker
name.

````
nicehash.timeout
````

Timeout for interaction with the Nicehash API


````
nicehash.profit_switch_threshold
````

The profit gain potential in % required before we will switch to a different
algorithm. A value of 0.04 means 4%.

````
use_max_power_limit_when_switching: true
````

If enabled the maximum power limit will be set before starting/switching algorithm.
This is useful to avoid throttling when two algorithms are loaded during the
switchover process and to ensure that the new algorithm can return a hashrate as
quickly as possible. If this setting is not enabled then the higher of the two
power limits associated with the algorithms will be set before the switchover.

````
nicehash.ports
````

Configured list of ports for Nicehash statrum endpoints.

````
nicehash.pool_fee
````

The nicehash pool fee - in most cases this will be 2%.

````
algorithms:
  single:
    - <list>
  double:
    - <list>
````

Algorithms to use with Minotaur. Algorithms will only be used if you have a
miner enabled that supports them and calibrated hashrate data.

````
hashrate_alert_threshold_percent: 3
````

Warn if the observed hashrate for an algorithm is 3% lower than the calibrated
rate.

````
algo_warmup_period_mins: 2
````

Suppress hashrate warnings for this period after an algorithm starts.

````
miners:
  ccminer:
    enable: true
    port: 3457
    ip: 127.0.0.1
    timeout: 10
  excavator:
    enable: true
    ip: 127.0.0.1
    port: 3456
    timeout: 10
````

Here we define the miners that Minotaur will execute. Minotaur will always
choose the most profitable algorithm and miner combination. Excavator is
supported directly via its API, other miners (currently ccminer, ccminer2 and
xmrig-nvidia) are supported via a shim project called Excavataur available here:

https://github.com/m4rkw/excavataur

````
logging:
  log_file: /var/log/minotaur/minotaur.log
  calibration_log_dir: /var/log/minotaur
  max_size_mb: 100
  log_file_count: 7
````

Logging parameters, fairly self-explanatory.

````
live_data:
  profitability_averages:
    - 900
    - 3600
    - 86400
  power_draw_averages:
    - 300
    - 600
    - 900
````

For the GS display - time periods to show profitability and power draw averages for.

````
xorg_display_no: 0
````

This is required for nvidia-settings to work.

````
electricity_per_kwh: 0.1194
electricity_currency: GBP
````

Here you should specify your power costs. These are factored into
algorithm-switching decisions and are also used to calculate profit for the GS
display.

````
calibration:
  hashrate_stabilisation_timeout_mins: 10
  hashrate_stabilisation_tolerance: 0.5
  hashrate_stabilisation_consecutive_readings_required: 5
  algorithm_start_timeout: 180
  power_tuning:
    enable: true
    decrement_watts: 10
    acceptable_loss_percent: 1
  update_calibration_data_over_time: true
  calibration_update_threshold_pc: 10
````

Settings for calibration runs. See the calibration section above.

````
leave_graphics_clocks_alone: true
````

Disable this to enable overclocking via device profiles. USE AT YOUR OWN RISK.

````
ignore_devices: [0,1,3]
````

Minotaur will ignore these GPU ids when running with --mine. You can also specify
device classes here

````
stats:
  enable: true
  stats_file: /var/log/minotaur/minotaur.csv
  algos_file: /var/log/minotaur/algorithms.csv
  max_size_mb: 10
  max_file_count: 7
````

Settings for statistics collection. If enable you can execute the reports.


## Donate

- XMR: 47zb4siDAi691nPW714et9gfgtoHMFnsqh3tKoaW7sKSbNPbv4wBkP11FT7bz5CwSSP1kmVPABNrsMe4Ci1F7Y2qLqT5ozd
- BTC: 1Bs4mCcyDcDCHfEisJqstEsmV5yzYcenJM


## Related projects

- Excavataur - https://github.com/m4rkw/excavataur
- gpustatd - https://github.com/m4rkw/gpustatd


## Credits

gordan-bobic for enormous amounts of help
