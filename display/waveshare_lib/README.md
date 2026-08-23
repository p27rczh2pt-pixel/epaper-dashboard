# Waveshare driver (vendored)

`epd7in5_V2.py` and `epdconfig.py` are vendored as-is from Waveshare's repo
(MIT license, header preserved in each file):

https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd

Only needed on the Pi Zero that drives the physical display — not on any
machine just running the Flask API or using `--preview`. If Waveshare
updates the driver upstream, re-fetch both files and diff before replacing.

Note: the current upstream driver's `RaspberryPi` backend in `epdconfig.py`
uses `spidev` + `gpiozero` (not `RPi.GPIO`) — see `requirements-display.txt`.
