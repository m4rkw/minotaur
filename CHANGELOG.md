````
30/01/2018 0.2 - initial release
30/01/2018 0.3 - bugfix
30/01/2018 0.4 - changes:
 - added more algorithms to the ccminer2 shim (alexis78)
 - removed non-working algorithms
 - bugfix: shim algorithms were not stopped if the hashrate was not detected
 - added P0/P1/P2 state to the gs display
 - fixed profile selection based on device/algorithm
 - ensure default profile is always loaded before stopping workers
 - don't crash if the miner backends all go away
 - apply reloaded profile settings for active devices on HUP
30/01/2018 0.5 - minor fixes
30/01/2018 0.6 - changes:
 - support for custom device classes
 - support for overclocking in calibration runs
 - ignore GPU/memory clock offsets in the default profile
 - bugfix: SIGHUP crashes gs
 - bugfix: fixed some gs display artefacts
 - added option to clean up workers for a specific device
 - bugfix: fixed setting of power limit during calibration
 - if calibrating without power tuning enabled, store the default power limit
   rather than the maximum observed power draw
 - fixed a crash when HUPing after removing an active calibration profile
 - tidied up gs display columns
 - fixed ccminer lyra2rev2 compatibility
30/01/2018 0.7 - changes:
- minor bugfix in nicehash library
- fix for ccminer jobs not being cleaned up on SIGINT when calibrating
31/01/2018 0.7.1 - changes:
- fixed minor gs rendering bug
- fixed crash when running blended algorithms
- enabled scrypt, sia, x11 and x13 in ccminer
31/01/2018 0.7.2 - changes:
- fixed an issue that can cause a crash under certain conditions
31/01/2018 0.7.3 - changes:
- bugfix: --cleanup not stopping workers
31/01/2018 0.7.4 - changes:
- show separate mBTC rates when running dual algos
- minor fixes and improvements
- fixed power throttling
- fixed margin display under low hashrate conditions
31/01/2018 0.7.5 - changes:
- added support for device pinning
- fixed minotaur not stopping workers on SIGINT
01/02/2018 0.8.4 - changes:
- rewrote a lot of the core code to make it cleaner, faster and more stable
- resolved some edge-cases
- fixed crash when theres no calibration data
- dont touch the power limit when calibrating in quick mode
02/02/2018 0.8.5 - changes:
- various stability fixes
- sensible config defaults
- added more flexible calibration parameters
02/02/2018 0.8.6 - changes:
- fixed an edge-case crash
- added quickstart mode
- added turbo calibration
02/02/2018 0.8.7 - fixed setting of power limits
02/02/2018 0.8.8 - changes:
- indicate when nicehash is down
- default to equihash in eu when nicehash is down
02/02/2018 0.8.9 - changes:
- use threading and queues to execute algo switches much faster
- added default algorthm to nicehash config for when the API is unavailable
- added workarounds for older cards that don't support setting a power limit
02/02/2018 0.8.9.1 - changes:
- misc bugfixes
- fixed calibration algorithm
03/02/2018 0.8.10 - changes:
- fixed clocks display on 780ti
- detect conflicting calibration runs
- fixed gs display when nicehash is down
- check for updates on startup
05/02/2018 0.8.11 - fix for ubuntu 16.04
05/02/2018 0.9 - changes:
- ethermine and ethminer support for ethereum mining
- fixed calculation of power costs
- various bugfixes and improvements
- start new algorithm worker before stopping the old one
- gs now shows all algos running on a device
07/02/2018 0.9.1 - various minor bugfixes
07/02/2018 0.9.2 - calibration crash fix
07/02/2018 0.9.3 - minor bugfix
07/02/2018 0.9.4 - minor bugfix
07/02/2018 0.9.5 - bugfix for gs crash
07/02/2018 0.9.6 - bugfix for occasional gs crash
07/02/2018 0.9.7 - changes:
- fixed total power calculation when more than one algo is running
- fixed crashes when running dual algos
08/02/2018 0.9.8 - changes:
- support for dynamic calibration updates
- added CSV stats collection
- basic profitability summary report
08/02/2018 0.9.8.1 - changes:
- bugfix for failure to reset device clocks on --cleanup
08/02/2018 0.9.8.2 - changes:
- fixed a bug with device pinning
08/02/2018 0.9.8.3 - changes:
- fixed a bug with device pinning
09/02/2018 0.9.8.4 - stats bugfix
10/02/2018 0.9.8.5 - changes:
- handle SIGTERM and cleanup workers
- fixed gs display with more than 3 avg time periods
- made gs exit cleanly on ctrl-c
- fixed HUP not un-ignoring devices
11/02/2018 0.9.8.6 - changes
- dont exit if we fail to get a stable hashrate reading - skip to the next algo
- added support for ZEC pool mining via flypool
11/02/2018 0.9.8.7 - bugfix for zec pool mining
11/02/2018 0.9.8.8 - added configurable pool fees
12/02/2018 0.9.8.9 - changes:
- exit gracefully if a worker is stopped externally during calibration
- added a temporary 35% offset to balance ZEC profitability
12/02/2018 0.9.8.10 - removed ZEC offset
12/02/2018 0.9.8.11 - minor bugfix
12/02/2018 0.9.8.12 - changes:
- added debug statements
12/02/2018 0.9.8.13 - changes:
- fix for calibrating with disabled miners
12/02/2018 0.9.8.14 - changes:
- fix for crash on startup when miners are running on a disabled pool
12/02/2018 0.9.8.15 - added some extra debug routines
13/02/2018 0.9.8.16 - changes:
- fixed ZEC block reward in example config
- use whattomine.com for profitability data
13/02/2018 0.9.9 - added monero ocean pool support
13/02/2018 0.9.9.1 - fixed stats bug
13/02/2018 0.9.9.2 changes:
- optimised gs display
- added self-upgrade feature
13/02/2018 0.9.9.3 - changes:
- added mobile display mode for gs
13/02/2018 0.9.9.4 - bugfix
14/02/2018 0.9.9.5 - various bugfixes related to devices that don't support power control
14/02/2018 0.9.9.6 - ewbf support (requires a shim)
14/02/2018 0.9.9.7 - various minor bugfixes
15/02/2018 0.9.9.8 - various minor bugfixes
18/02/2018 1.0 - changes:
- fanotaur is now gpustatd
- gpustatd does all the nvidia device polling
- power regulation is now done in gpustatd
- added support for custom excavator params
- option to set max power limit when starting/switching algo
- if not using max power when switching the higher limit of the two algos will be set
- removed power limits from device profiles
- added support for zclmine.pro for ZCL mining
- added config param for system draw
- added support for nicehash pool fee in profit calculation
- added support for miningpoolhub
18/02/2018 1.0.1 - minor bugfix
18/02/2018 1.0.2 - added support for overriding max power limit in config
19/02/2018 1.0.3 - minor bugfix
19/02/2018 1.0.4 - changes:
- fix for algo disabling
- disabled excavator for ethermine
19/02/2018 1.0.5 - changes:
- re-enabled excavator for ethermine
19/02/2018 1.0.7 - disabled excavator with ethermine (not compatible)
19/02/2018 1.0.8 - changes:
- switch immediately on startup if the active pool is disabled
- fix for crash when running with disabled algos
- added html gs output method
20/02/2018 1.0.9 - minor bugfix
20/02/2018 1.0.10 - fixed --algos method
20/02/2018 1.0.11 - added generic pool support
21/02/2018 1.1 - changes:
- set up new donation mechanism
- fix for race condition crash
- don't wait for a hashrate before stopping the old worker
- additionally process /etc/minotaur.conf.d/*.conf
- track time since last change
- apply OC profiles and power limits on HUP
- log device and total watts to csv
- blank fields from gpu_t onwards for secondary algos on a device
21/02/2018 1.1.1 - fix for incorrect power logs
21/02/2018 1.1.2 - changes:
- fixed gs time format
- fix for crash during calibration
- added better handling of calibration with a disabled pool
- enabled ethminer for nicehash
- fixed crash on HUP
- crash bugfix
- stats bugfix
- stopped donation runs overlapping
- exclude donating devices from profitability calculations
````
